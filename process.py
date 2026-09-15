import os
import numpy as np
import pandas as pd
import osrparse
import traceback
from slider import Beatmap, Slider, Spinner

# --- CONFIGURATION ---
REPLAY_DIR = "/content/content/osr"
BEATMAP_DIR = "/content/maps/beatmaps"
OUTPUT_DIR = "/content/data-v9"
CSV_PATH = "/content/filtered_index_5.csv"

PLAYFIELD_W = 512
PLAYFIELD_H = 384
dt = 1000 / 60

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- HELPER FUNCTIONS ---
def to_ms(t):
    if hasattr(t, 'total_seconds'): return t.total_seconds() * 1000
    return float(t)

def get_slider_position(obj, current_time):
    start_ms = to_ms(obj.time)
    end_ms = to_ms(obj.end_time)
    elapsed = current_time - start_ms
    total_duration = end_ms - start_ms

    if total_duration <= 0 or elapsed < 0: return obj.position.x, obj.position.y
    if elapsed > total_duration:
        return (obj.curve(1.0).x, obj.curve(1.0).y) if obj.repeat % 2 == 1 else (obj.curve(0.0).x, obj.curve(0.0).y)

    span_duration = total_duration / obj.repeat
    current_lap = int(elapsed / span_duration)
    current_lap = min(current_lap, obj.repeat - 1)
    time_in_span = elapsed - (current_lap * span_duration)
    progress = time_in_span / span_duration
    if current_lap % 2 == 1: progress = 1.0 - progress

    try:
        pos = obj.curve(progress)
        return pos.x, pos.y
    except:
        return obj.position.x, obj.position.y

def get_target_context(current_time, hit_objects, search_start_index):
    idx = search_start_index
    SLIDER_LOOKAHEAD_MS = 50.0

    while idx < len(hit_objects):
        obj = hit_objects[idx]
        end_ms = to_ms(obj.end_time) if hasattr(obj, 'end_time') else to_ms(obj.time)
        if end_ms > current_time: break
        idx += 1

    if idx >= len(hit_objects): return 0.5, 0.5, 0, 0, idx, 0.5, 0.5

    obj = hit_objects[idx]
    start_ms = to_ms(obj.time)

    if hasattr(obj, 'repeat'): # Slider
        obj_type = 1.0
        if current_time < start_ms:
            tx, ty = obj.position.x / 512, obj.position.y / 384
            t_delta = (start_ms - current_time) / 1000.0
        else:
            raw_x, raw_y = get_slider_position(obj, current_time + SLIDER_LOOKAHEAD_MS)
            tx = raw_x / 512
            ty = raw_y / 384
            t_delta = 0.0
    elif isinstance(obj, Spinner): # Spinner
        obj_type = 2.0
        tx, ty = 0.5, 0.5
        t_delta = (start_ms - current_time) / 1000.0
    else: # Circle
        obj_type = 0.0
        tx = obj.position.x / 512
        ty = obj.position.y / 384
        t_delta = (start_ms - current_time) / 1000.0

    next_idx = idx + 1
    if next_idx < len(hit_objects):
        next_obj = hit_objects[next_idx]
        ntx = next_obj.position.x / 512
        nty = next_obj.position.y / 384
    else:
        ntx, nty = tx, ty

    return tx, ty, t_delta, obj_type, idx, ntx, nty

def get_perfect_click_label(current_time, hit_objects, cursor_x, cursor_y, cs_radius):
    def to_ms(t):
        if hasattr(t, 'total_seconds'): return t.total_seconds() * 1000
        return t

    SIGMA = 8.0
    max_label = 0.0

    # 1. Calculate Thresholds
    # We use a slightly larger radius (1.5x) to account for Stacking
    # since we can't calculate exact stack positions.
    # We normalized cursor_x/y to 0-1, so we must normalize radius too.
    # osu! width is 512.
    normalized_radius = (cs_radius * 1.5) / 512.0

    # Pre-calculate squared radius to avoid sqrt calls (faster)
    radius_sq = normalized_radius ** 2

    for obj in hit_objects:
        start = to_ms(obj.time)
        end = to_ms(obj.end_time) if hasattr(obj, 'end_time') else start

        if end < current_time - 100: continue
        if start > current_time + 100: break

        # --- TEMPORAL CHECK ---
        val = 0.0
        if hasattr(obj, 'repeat') or isinstance(obj, Spinner):
            if current_time < start:
                diff = current_time - start
                val = np.exp(-(diff**2) / (2 * SIGMA**2))
            elif current_time > end:
                diff = current_time - end
                val = np.exp(-(diff**2) / (2 * SIGMA**2))
            else:
                val = 1.0
        else:
            diff = current_time - start
            val = np.exp(-(diff**2) / (2 * SIGMA**2))

        max_label = max(max_label, val)

    return max_label

def process_pair(replay_path, beatmap_path, is_perfect=True, min_length=190):
    try:
        replay = osrparse.Replay.from_path(replay_path)
        beatmap = Beatmap.from_path(beatmap_path)

        r_data = replay.replay_data
        if not r_data: return None, None

        times = np.array([d.time_delta for d in r_data])
        cumulative_times = np.cumsum(times)
        xs = np.array([d.x for d in r_data])
        ys = np.array([d.y for d in r_data])

        start_time = cumulative_times[0]
        end_time = cumulative_times[-1]

        # Safety Checks
        if end_time - start_time < 1000: return None, None

        # Resample
        timestamps = np.arange(start_time, end_time, dt)
        interp_x = np.interp(timestamps, cumulative_times, xs)
        interp_y = np.interp(timestamps, cumulative_times, ys)

        hit_objects = beatmap.hit_objects()
        cs = beatmap.cs()

        # Radius in pixels
        radius_px = 54.4 - 4.48 * cs

        # --- LOGIC BRANCH: VALIDATION ---
        # If it's NOT an FC, we need to find which parts are garbage.
        valid_mask = None

        if not is_perfect:
            valid_mask = np.zeros(len(timestamps), dtype=bool)

            # Use a forgiving radius (1.5x) to account for stacking if library doesn't support it
            check_radius = radius_px * 1.5

            for obj in hit_objects:
                hit_time = to_ms(obj.time)

                # Find frame at hit time
                idx = np.searchsorted(timestamps, hit_time)
                if idx >= len(timestamps): continue

                # Check distance
                px_at_hit = interp_x[idx]
                py_at_hit = interp_y[idx]
                dist = np.sqrt((px_at_hit - obj.position.x)**2 + (py_at_hit - obj.position.y)**2)

                # If HIT: Mark previous 600ms as valid training data
                if dist <= check_radius:
                    start_idx = max(0, idx - 36) # ~600ms (36 frames)
                    valid_mask[start_range_idx : idx + 1] = True

        # --- MAIN LOOP ---
        features = []
        labels = []
        ho_index = 0
        label_search_idx = 0

        # Buffer for non-FC segments
        all_segments = []
        current_features = []
        current_labels = []

        for i, t in enumerate(timestamps):
            # 1. FILTERING (Only for non-FC)
            if not is_perfect:
                if not valid_mask[i]:
                    # Bad frame. If we have a segment built up, save it.
                    if len(current_features) > min_length:
                        all_segments.append((np.array(current_features, dtype=np.float32),
                                             np.array(current_labels, dtype=np.float32)))
                    current_features = []
                    current_labels = []

                    # IMPORTANT: We must still advance context pointers!
                    # Run context logic but don't save data
                    _, _, _, _, ho_index, _, _ = get_target_context(t, hit_objects, ho_index)
                    continue

            # 2. Inputs
            curr_x = interp_x[i] / PLAYFIELD_W
            curr_y = interp_y[i] / PLAYFIELD_H

            tx, ty, t_delta, obj_type, new_idx, ntx, nty = get_target_context(t, hit_objects, ho_index)
            ho_index = new_idx

            delta_x = tx - curr_x
            delta_y = ty - curr_y

            # 3. Label Generation (Distance Gated)
            while label_search_idx < len(hit_objects):
                end_t = hit_objects[label_search_idx].end_time if hasattr(hit_objects[label_search_idx], 'end_time') else hit_objects[label_search_idx].time
                if to_ms(end_t) < t - 100: label_search_idx += 1
                else: break

            relevant_objects = hit_objects[label_search_idx : label_search_idx + 5]
            perfect_click = get_perfect_click_label(t, relevant_objects, curr_x, curr_y, radius_px)

            # 4. Save
            input_row = [curr_x, curr_y, tx, ty, delta_x, delta_y, t_delta, obj_type, ntx, nty]

            if i < len(timestamps) - 1:
                next_x = interp_x[i+1] / PLAYFIELD_W
                next_y = interp_y[i+1] / PLAYFIELD_H
                label_row = [next_x, next_y, perfect_click]

                if is_perfect:
                    # Continuous appending for FCs
                    features.append(input_row)
                    labels.append(label_row)
                else:
                    # Segmented appending for Non-FCs
                    current_features.append(input_row)
                    current_labels.append(label_row)

        # Finalize
        if is_perfect:
            return [(np.array(features, dtype=np.float32), np.array(labels, dtype=np.float32))]
        else:
            if len(current_features) > min_length:
                all_segments.append((np.array(current_features, dtype=np.float32),
                                     np.array(current_labels, dtype=np.float32)))
            return all_segments

    except Exception as e:
        return None


# --- MAIN EXECUTION ---

# DEFINE YOUR TRAINING SEQ_LEN HERE
TRAIN_SEQ_LEN = 180
# Set buffer slightly higher so we have wiggle room for random sampling
MIN_SEGMENT_LEN = TRAIN_SEQ_LEN + 10

df = pd.read_csv(CSV_PATH)
subset = df.head(30000)

print(f"Processing {len(subset)} replays...")

processed_count = 0

for index, row in subset.iterrows():
    r_hash = row['replayHash']
    b_hash = row['beatmapHash']

    # 1. Get FC Status
    is_fc = row['performance-IsFC']
    if isinstance(is_fc, str):
        is_fc = (is_fc.lower() == 'true')

    r_path = os.path.join(REPLAY_DIR, f"{r_hash}.osr")
    b_path = os.path.join(BEATMAP_DIR, f"{b_hash}.osu")

    if os.path.exists(r_path) and os.path.exists(b_path):
        segments = process_pair(r_path, b_path, is_perfect=is_fc, min_length=MIN_SEGMENT_LEN)

        if segments:
            for i, (X, Y) in enumerate(segments):

                save_path = os.path.join(OUTPUT_DIR, f"data_{processed_count}_part{i}.npz")

                np.savez_compressed(save_path, features=X, labels=Y)

            processed_count += 1

            if processed_count % 100 == 0:
                print(f"Processed {processed_count} replays...")

print("Done.")