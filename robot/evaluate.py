#!/usr/bin/env python
"""
Evaluate a trained ACTPolicy on the SO-ARM101 follower arm.

Workaround for lerobot-record issue #2597 (infinite reset loop after episode 0
when using --policy.path without --teleop). This script owns the control loop
directly so we never touch the record CLI.

Usage:
    conda activate lerobot
    set -a && source .env && set +a
    python robot/evaluate.py --n_episodes 10
"""

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.policies.factory import make_pre_post_processors
from lerobot.robots.so_follower import SO101Follower
from lerobot.robots.so_follower.config_so_follower import SO101FollowerConfig
from lerobot.utils.robot_utils import precise_sleep

MOTOR_NAMES = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

DEFAULT_CHECKPOINT = (
    "outputs/train/act_pick_object/checkpoints/last/pretrained_model"
)


def load_policy(
    checkpoint_path: Path,
) -> tuple[ACTPolicy, object, object]:
    """Load policy and its normalization pipelines from a pretrained checkpoint.

    Runs one dummy forward pass after loading to pre-compile MPS Metal kernels.
    Without this, the first 2-3 seconds of episode 1 run at ~6 Hz instead of 30 Hz.
    """
    policy = ACTPolicy.from_pretrained(str(checkpoint_path))
    preprocessor, postprocessor = make_pre_post_processors(
        policy_cfg=policy.config,
        pretrained_path=str(checkpoint_path),
    )

    print("  Warming up MPS kernels (first inference compile) ...")
    dummy = {
        "observation.state": torch.zeros(6),
        "observation.images.top": torch.zeros(3, 480, 640),
    }
    dummy = preprocessor(dummy)
    with torch.no_grad():
        policy.select_action(dummy)
    policy.reset()
    print("  Warmup done.")

    return policy, preprocessor, postprocessor


def build_robot(port: str, camera_index: int = 0) -> SO101Follower:
    """Instantiate follower arm with top-down webcam. Does not connect."""
    config = SO101FollowerConfig(
        id="agent47_follower",
        port=port,
        cameras={
            "top": OpenCVCameraConfig(
                index_or_path=camera_index,
                fps=30,
                width=640,
                height=480,
            )
        },
    )
    return SO101Follower(config)


def raw_obs_to_batch(raw_obs: dict) -> dict[str, torch.Tensor]:
    """Convert robot observation dict to the format the preprocessor expects.

    Motor positions stay as a flat state vector; the camera image is converted
    from (H, W, C) uint8 to (C, H, W) float32 in [0, 1].
    No batch dimension here — the preprocessor's to_batch step adds it.
    """
    state = torch.tensor(
        [raw_obs[f"{m}.pos"] for m in MOTOR_NAMES], dtype=torch.float32
    )

    img = raw_obs["top"]  # (H, W, C) uint8
    img_tensor = torch.from_numpy(np.ascontiguousarray(img))
    img_tensor = img_tensor.permute(2, 0, 1).float() / 255.0  # (C, H, W)

    return {
        "observation.state": state,
        "observation.images.top": img_tensor,
    }


def action_tensor_to_dict(action: torch.Tensor) -> dict[str, float]:
    """Convert policy output [1, 6] tensor to {motor.pos: float} robot action."""
    vals = action.squeeze(0).tolist()
    return {f"{name}.pos": val for name, val in zip(MOTOR_NAMES, vals)}


def run_episode(
    robot: SO101Follower,
    policy: ACTPolicy,
    preprocessor,
    postprocessor,
    fps: int,
    duration_s: float,
) -> tuple[int, float]:
    """Run one autonomous episode. Returns (steps_executed, actual_fps)."""
    policy.reset()
    period = 1.0 / fps
    t_start = time.perf_counter()
    deadline = t_start + duration_s
    step = 0

    while time.perf_counter() < deadline:
        t0 = time.perf_counter()

        raw_obs = robot.get_observation()
        batch = raw_obs_to_batch(raw_obs)
        batch = preprocessor(batch)

        with torch.no_grad():
            action = policy.select_action(batch)

        action = postprocessor(action)
        robot.send_action(action_tensor_to_dict(action))

        step += 1
        elapsed = time.perf_counter() - t0
        precise_sleep(max(0.0, period - elapsed))

    actual_fps = step / (time.perf_counter() - t_start)
    return step, actual_fps


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate trained ACT policy on SO-ARM101")
    parser.add_argument(
        "--checkpoint",
        default=DEFAULT_CHECKPOINT,
        help="Path to pretrained_model directory",
    )
    parser.add_argument("--n_episodes", type=int, default=5)
    parser.add_argument(
        "--duration_s",
        type=float,
        default=25.0,
        help="Episode length in seconds (match training episode_time_s)",
    )
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--camera_index", type=int, default=0)
    args = parser.parse_args()

    port = os.environ.get("SO101_FOLLOWER_PORT")
    if not port:
        sys.exit("SO101_FOLLOWER_PORT not set. Run: set -a && source .env && set +a")

    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        sys.exit(f"Checkpoint not found: {checkpoint_path}")

    print(f"Loading policy from {checkpoint_path} ...")
    policy, preprocessor, postprocessor = load_policy(checkpoint_path)
    print(f"  device: {policy.config.device}")

    print(f"Connecting to arm on {port} ...")
    robot = build_robot(port, args.camera_index)
    # calibrate=False: calibration files already written to motor EEPROM from previous sessions
    robot.connect(calibrate=False)
    print("  connected.\n")

    try:
        for ep in range(args.n_episodes):
            print(f"── Episode {ep + 1}/{args.n_episodes} ──")
            print(f"   Running for {args.duration_s}s at {args.fps} FPS ...")

            steps, actual_fps = run_episode(
                robot, policy, preprocessor, postprocessor, args.fps, args.duration_s
            )
            print(f"   Done. {steps} steps @ {actual_fps:.1f} Hz actual.")
            if actual_fps < args.fps * 0.85:
                print(f"   WARNING: running at {actual_fps:.1f} Hz (target {args.fps} Hz) — policy timing is off.")

            if ep < args.n_episodes - 1:
                input("\n   Move arm to start position, reposition object, then press Enter...")
                print()

    finally:
        robot.disconnect()
        print("\nArm disconnected.")


if __name__ == "__main__":
    main()
