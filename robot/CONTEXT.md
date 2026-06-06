# Agent 47 Robotics — Current Context

Snapshot as of the end of Week 2 dry-run + dataset recording session.

## Where things stand

**Done:**
- Hardware: SO-ARM101 leader + follower arms purchased, assembled, calibrated
- Teleoperation: working at 60 Hz with rerun viewer
- Workspace: 20×20cm taped square with white paper background, fixed top-down webcam
- Dry run: 5 episodes recorded, watched back, framing/grasps verified
- Real dataset: 24 clean episodes at `raystanlee/pick_object_drop_blue_bin` (deleted 1 bad episode out of original 25)

**In progress:**
- Train ACT on Mac M4 Pro overnight (MPS backend)

**Next:**
- Evaluate trained policy on physical arm
- If success rate ≥50%, move to Week 3 (Agent 47 integration)
- If lower, record more episodes and retrain

## Hardware

### SO-ARM101 kit (PartaBot Full Kit, $469, pre-assembled)

- **Follower arm**: 12V/5A power, high-torque motors (heavy)
- **Leader arm**: 5V/4A power, low-torque (controller)
- Both pre-assembled in gray PLA+
- Waveshare BusLinker boards with white DVG sockets
- Kit included 1080p USB-A webcam, table clamps, USB-C cables

### Calibrated arm IDs (use these exact strings)

- Follower: `agent47_follower` on port `/dev/tty.usbmodem5AE60581581`
- Leader: `agent47_leader` on port `/dev/tty.usbmodem5AE60587941`

**Ports may shift between sessions.** If commands fail with empty motor list, run `lerobot-find-port` and update `.env`. Calibration files at `~/.cache/huggingface/lerobot/calibration/`.

### Camera

- 1080p webcam from kit, mounted on phone tripod via spring clamp (1/4-20 thread didn't match cleanly)
- Top-down view (~30cm above workspace)
- Plugged directly into Mac USB
- Top-down chosen over front-facing because front view caused arm body to occlude workspace during grasp

### Workspace

- 20×20cm green-tape square on dark desk
- White printer paper taped down inside (green tape covers paper edges, holds it flat)
- Blue paper-cup bin (~10cm diameter) fixed in left portion of workspace
- Object: small cap, surface darkened with marker for contrast against white paper
- Bin position is fixed across all 25 recorded episodes; only the object position varies

### To order

- **UGREEN Revodok Pro 106 USB-C Hub** (~$30-50). With Mac charger in PD port, this solves intermittent USB power issues that plague the 2-BusLinkers-plus-webcam load.

## Dataset

- **Repo ID**: `raystanlee/pick_object_drop_blue_bin`
- **Local path**: `~/.cache/huggingface/lerobot/raystanlee/pick_object_drop_blue_bin/`
- **Task description**: "Pick up the object and drop it in the blue bin"
- **Episodes**: 24 (originally 25, deleted bad episode 3)
- **Frames**: 17,627
- **Camera key**: `observation.images.top`
- **FPS**: 30
- **Episode length**: ~25s recording + ~10s reset
- **NOT pushed to HuggingFace Hub yet** (push later for training on remote GPUs or backup)

## Recording command (reference, for adding more episodes)

```bash
lerobot-record \
  --robot.type=so101_follower \
  --robot.port=$SO101_FOLLOWER_PORT \
  --robot.id=agent47_follower \
  --robot.cameras="{ top: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}" \
  --teleop.type=so101_leader \
  --teleop.port=$SO101_LEADER_PORT \
  --teleop.id=agent47_leader \
  --display_data=true \
  --dataset.repo_id=raystanlee/pick_object_drop_blue_bin \
  --dataset.single_task="Pick up the object and drop it in the blue bin" \
  --dataset.num_episodes=25 \
  --dataset.episode_time_s=25 \
  --dataset.reset_time_s=10 \
  --dataset.push_to_hub=false \
  --resume=true     # if adding to existing dataset
```

## Pruning bad episodes

```bash
lerobot-edit-dataset \
  --repo_id=raystanlee/pick_object_drop_blue_bin \
  --operation.type=delete_episodes \
  --operation.episode_indices="[3]"     # or [3,7,12] for multiple
```

After deletion, episodes are renumbered. What was 4 becomes 3, etc.

## Hardware gotchas (learned the hard way)

1. **BusLinker → first servo cable can ship disconnected.** Symptom: `Found motors: {}`. Fix: push the 3-pin cable firmly into the white DVG socket.

2. **JST connectors are marginal.** Power-cycle the arm to fix many "no motors found" errors.

3. **Power supplies must match.** 12V → follower (heavy motors), 5V → leader (low torque). Wrong voltage makes joint LEDs blink (over-volt protection).

4. **PWR LED on the BusLinker lights up from USB alone.** Doesn't mean servos are powered. Test by trying to move a joint by hand. Stiff = powered. Floppy = not.

5. **Camera mount screws can jam the gripper if too long.** For first datasets, don't mount the camera on the arm at all.

6. **macOS USB can't reliably power 2 BusLinkers + webcam.** The UGREEN hub fixes this. Until then, expect random handshake failures.

7. **Bus cables pop out mid-session.** Movement strain on JST connectors. Zip-tie strain relief once everything works.

8. **macOS camera permissions.** Terminal needs camera access in System Settings → Privacy & Security → Camera. Quit (Cmd+Q) and reopen Terminal after granting.

9. **iPhone Continuity Camera shuffles indices.** Lock the iPhone or disable Continuity Camera (Settings → General → AirPlay & Continuity → Continuity Camera → off) for stable webcam index.

10. **Calibration excludes wrist_roll** (continuous rotation, no hard stops). All 5 other joints need full sweep with POS between MIN/MAX before pressing Enter.

11. **Camera "TimeoutError waiting for frame"** between sessions: unplug-replug the webcam USB. Fixes 90% of camera death issues.

12. **Avoid `sudo lerobot-record`.** It creates root-owned files in `~/.cache/huggingface/lerobot/` that block later `rm`. Cleanup needs `sudo rm -rf` or `sudo chown -R $(whoami)`. Doesn't fix the keyboard listener issue anyway.

## The macOS keyboard listener issue (unsolved)

LeRobot's `lerobot-record` uses pynput to listen for keyboard controls:
- Right arrow → save episode and continue
- Left arrow → discard and re-record
- Escape → stop session, save what's done

**These do not work on Ray's M4 Pro.** Tried:
- Granting Terminal Accessibility permission (System Settings → Privacy & Security → Accessibility)
- Adding the Python binary itself (`/opt/miniconda3/envs/lerobot/bin/python3.12`) to Accessibility
- Running with `sudo`
- Both terminal-focused and rerun-viewer-focused

In all cases, pressing keys prints raw escape sequences (`^[`) to the terminal instead of being captured by pynput.

**Workaround:**
- Use timer-based recording (`episode_time_s` and `reset_time_s` flags).
- For breaks, Ctrl+C during the "Reset the environment" phase (NOT mid-episode — leaves dataset inconsistent).
- Resume sessions with `--resume=true`.
- Prune bad episodes after recording with `lerobot-edit-dataset`.

## Critical teleop discipline

Look ONLY at the camera feed on screen during teleoperation, never at the physical follower arm. The trained policy will only see what the camera saw. Watching the real arm trains your hand to compensate in ways the policy can't reproduce at inference time.

## Why webcam, not RealSense

The Intel RealSense D435I (currently mounted on the Orin Nano for the `capture_scene` perception server) was the obvious choice but was rejected for the LeRobot dataset because:

- ACT is RGB-only; depth would be ignored
- RealSense pulls more USB power, worsening the intermittent power issues
- More pretrained RGB models on HuggingFace for fine-tuning
- Real bottleneck is teleop consistency, not camera quality
- Keeps the Orin's perception server intact

The RealSense stays on the Orin. Plan to add it as a *second* camera view in Week 3-4 once the single-camera pipeline works.

## 3-week roadmap

**Week 1 — Conceptual grounding + hardware setup** ✓ DONE
- Read ACT paper, π₀ blog, GEN-1 post
- LeRobot sim tutorials (LIBERO, aloha sim)
- Hardware assembled and calibrated
- Teleop running at 60 Hz

**Week 2 — First real policy** ← currently here
- ✓ Workspace setup (taped square, object, bin)
- ✓ Recorded 24 clean episodes of pick-and-place
- → Train ACT on Mac M4 Pro overnight (MPS backend)
- → Deploy back to physical arm, evaluate
- Target: 50-70% success rate

**Week 3 — Agent 47 integration**
- Port policy to Orin Nano OR keep on Mac (decision TBD based on Orin compute)
- Build `manipulation_tool.py` wrapping ACTPolicy
- Add to `mcp.json`, register with Haiku intent classifier
- End-to-end demo: Telegram message → `capture_scene` → `execute_manipulation` → `capture_scene` → reply with before/after images
- Document, commit, video writeup

## Deferred to Week 4+

- SmolVLA, π₀, GR00T fine-tuning (after ACT works cleanly)
- RealSense as second camera / wrist-mounted depth views
- Multi-camera ACT
- RL fine-tuning (HIL-SERL) on top of imitation
- Sim2Real via Isaac Sim
- LeKiwi mobile base (arms transfer over, no upgrade lost)

## Decision rationale for buying the arm

Evaluated three directions for competitive-advantage learning:

| Option | Cost | Verdict |
|--------|------|---------|
| GPU (RTX 3090) | Rentable on Vast.ai @ $0.25/hr | No urgency to buy |
| Drone | $$$ | Niche, space-constrained, off-frontier |
| Robot arm (SO-ARM101) | $469 | Plugs into LeRobot/HF ecosystem, compounds with Orin+RealSense stack, rare DS skill |

Rule of thumb: **buy what you can't rent, rent compute when needed.**
