import cv2
import numpy as np

# =========================
# 1. USER SETTINGS
# =========================
IMAGE_PATH = "plate_red.jpg"       # <-- Path to your image with the 7 red circles
OUT_IMG_PATH = "red_fit_check.png" # Visual check: cyan fitted circles over your red lines
OUT_SCAD_PATH = "plate_3d.scad"

ROD_DIAM_MM = 8.0                  # Known diameter of H5 and H7 (H5 == H7)
USE_2D_TILT = True                 # True: corrects both X & Y tilt; False: Y-tilt only
EST_PLATE_WIDTH_MM = 30.0          # Physical plate width for 3D SCAD model
EST_THICKNESS_MM = 5.0             # Measure thickness physically with calipers!


def fit_circle_geometric(xs: np.ndarray, ys: np.ndarray):
    """Algebraic Kasa initialization + outlier trim + Gauss-Newton geometric circle fit."""
    xm, ym = float(np.mean(xs)), float(np.mean(ys))
    dx, dy = xs - xm, ys - ym

    # Step 1: Algebraic initial estimate
    A = np.column_stack([2.0 * dx, 2.0 * dy, np.ones_like(dx)])
    b = dx**2 + dy**2
    cx_rel, cy_rel, c0 = np.linalg.lstsq(A, b, rcond=None)[0]
    cx, cy = xm + cx_rel, ym + cy_rel
    r = float(np.sqrt(max(1.0, cx_rel**2 + cy_rel**2 + c0)))

    # Step 2: Trim stray outlier pixels (> 3*MAD or > 4 px from initial circle)
    d = np.hypot(xs - cx, ys - cy)
    err = np.abs(d - r)
    mad = np.median(err)
    keep = err <= max(4.0, 3.5 * mad)
    if np.sum(keep) >= 20:
        xs, ys = xs[keep], ys[keep]

    # Step 3: Gauss-Newton refinement minimizing sum((d_i - r)^2)
    for _ in range(10):
        d = np.hypot(xs - cx, ys - cy)
        d = np.maximum(d, 1e-6)
        r = float(np.mean(d))
        J = np.column_stack([-(xs - cx) / d, -(ys - cy) / d, -np.ones_like(d)])
        delta = np.linalg.lstsq(J, -(d - r), rcond=None)[0]
        cx += float(delta[0])
        cy += float(delta[1])
        r += float(delta[2])
        if np.linalg.norm(delta) < 1e-4:
            break

    rms_px = float(np.sqrt(np.mean((np.hypot(xs - cx, ys - cy) - r) ** 2)))
    return float(cx), float(cy), float(r), rms_px, xs, ys


def extract_red_circles(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    h, w = img.shape[:2]
    b, g, r = cv2.split(img)

    # Color-excess mask catches thin anti-aliased red over black, gray, OR white paint
    redness = r.astype(np.int16) - np.maximum(g, b).astype(np.int16)
    red_mask = ((redness > 35) & (r > 55)).astype(np.uint8) * 255

    # Dilate slightly ONLY for grouping each ring into one connected component
    group_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    grouped = cv2.dilate(red_mask, group_kernel, iterations=1)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(grouped)

    circles = []
    for cid in range(1, num_labels):
        bx, by, bw, bh, _ = stats[cid]
        # Reject tiny specks (like dust inside H5) and invalid aspect ratios
        if not (0.11 * w <= bw <= 0.65 * w and 0.11 * w <= bh <= 0.65 * w):
            continue
        if not (0.75 <= bw / bh <= 1.35):
            continue

        # Extract ONLY the original un-dilated red stroke pixels for this component
        ys, xs = np.where((labels == cid) & (red_mask > 0))
        if xs.size < 60:
            continue

        xs_f, ys_f = xs.astype(np.float64), ys.astype(np.float64)
        cx, cy, rad, rms_px, clean_x, clean_y = fit_circle_geometric(xs_f, ys_f)

        # Optional ellipse check to measure aspect ratio (minor / major)
        pts = np.column_stack([clean_x, clean_y]).astype(np.float32)
        (_, (ax1, ax2), _) = cv2.fitEllipse(pts)
        aspect = min(ax1, ax2) / max(ax1, ax2)

        circles.append((cx, cy, rad, rms_px, aspect))

    # Separate outer 4 holes vs centerline 3 holes by X position
    outer4 = [c for c in circles if abs(c[0] - w / 2.0) > 0.18 * w]
    center3 = [c for c in circles if abs(c[0] - w / 2.0) <= 0.18 * w]
    outer4.sort(key=lambda c: c[1])
    row1 = sorted(outer4[:2], key=lambda c: c[0]) if len(outer4) >= 2 else outer4
    row2 = sorted(outer4[2:4], key=lambda c: c[0]) if len(outer4) >= 4 else []
    center3.sort(key=lambda c: c[1])

    ordered = row1 + row2 + center3
    return img, ordered, w, h


def fit_camera_angle_scale(ordered, w, h, rod_diam_mm=8.0, use_2d=True):
    """Solves S(x, y) = a + b*dx + c*dy [px/mm] enforcing H1=H2=H3=H4 and H5=H7=8.0 mm."""
    eq_indices = [0, 1, 2, 3, 4, 6]
    d_est = 5.0

    for _ in range(3):
        A, rhs = [], []
        for idx in eq_indices:
            cx, cy, r, _, _ = ordered[idx]
            D = 2.0 * r
            xn = (cx - w / 2.0) / 1000.0
            yn = (cy - h / 2.0) / 1000.0
            if idx < 4:
                wt = d_est
                row = [wt / D, wt * xn / D, wt * yn / D, -wt] if use_2d else [wt / D, wt * yn / D, -wt]
                A.append(row)
                rhs.append(0.0)
            else:
                wt = rod_diam_mm
                row = [wt / D, wt * xn / D, wt * yn / D, 0.0] if use_2d else [wt / D, wt * yn / D, 0.0]
                A.append(row)
                rhs.append(1.0)

        params = np.linalg.lstsq(np.array(A), np.array(rhs), rcond=None)[0]
        if use_2d:
            a, b, c, u = params
        else:
            a, c, u = params
            b = 0.0
        d_est = 1.0 / u

    def scale_fn(x, y):
        return a + b * ((x - w / 2.0) / 1000.0) + c * ((y - h / 2.0) / 1000.0)

    return scale_fn, d_est, (a, b, c)


def integrate_distance_mm(p1, p2, scale_fn, steps=20):
    dx = (p2[0] - p1[0]) / steps
    dy = (p2[1] - p1[1]) / steps
    ds_px = np.hypot(dx, dy)
    total_mm = 0.0
    for k in range(steps):
        t = (k + 0.5) / steps
        total_mm += ds_px / scale_fn(p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
    return total_mm


def main():
    img, ordered, w, h = extract_red_circles(IMAGE_PATH)
    if len(ordered) != 7:
        print(f"Warning: found {len(ordered)} red circles instead of 7 (adjust redness > 35 if needed).")
        return

    labels = [
        "H1_top_left", "H2_top_right", "H3_mid_left", "H4_mid_right",
        "H5_rod_upper", "H6_center_large", "H7_rod_lower",
    ]

    scale_fn, d_corner_fit, (a, b, c) = fit_camera_angle_scale(
        ordered, w, h, ROD_DIAM_MM, USE_2D_TILT
    )

    ox = np.mean([ordered[i][0] for i in range(4)])
    oy = np.mean([ordered[i][1] for i in range(4)])
    h5, h7 = ordered[4], ordered[6]
    roll_rad = np.arctan2(h7[0] - h5[0], h7[1] - h5[1])
    cos_r, sin_r = np.cos(-roll_rad), np.sin(-roll_rad)

    print(f"\nImage: {w} x {h} px")
    print(f"Scale plane S(x,y) = {a:.3f} + {b:.3f}*dx_k + {c:.3f}*dy_k [px/mm]")
    print(f"Fitted top 4-hole diameter: {d_corner_fit:.3f} mm | Roll: {np.degrees(roll_rad):.2f} deg\n")
    print(
        f"{'Hole':<16} {'X_px':>7} {'Y_px':>7} {'Diam_px':>8} {'FitRMS':>6} {'Ellip':>6} "
        f"| {'X_mm':>7} {'Y_mm':>7} {'Diam_mm':>8}"
    )
    print("-" * 88)

    cad_holes = []
    vis = img.copy()
    for i, (cx, cy, r, rms_px, aspect) in enumerate(ordered):
        s_local = scale_fn(cx, cy)
        d_mm = (2.0 * r) / s_local

        dx_raw, dy_raw = cx - ox, cy - oy
        dx_rot = dx_raw * cos_r - dy_raw * sin_r
        dy_rot = dx_raw * sin_r + dy_raw * cos_r

        x_mm = np.sign(dx_rot) * integrate_distance_mm((ox, oy), (cx, oy), scale_fn)
        y_mm = np.sign(dy_rot) * integrate_distance_mm((ox, oy), (ox, cy), scale_fn)
        cad_holes.append((labels[i], x_mm, y_mm, d_mm))

        print(
            f"{labels[i]:<16} {cx:7.2f} {cy:7.2f} {2*r:8.2f} {rms_px:6.2f} {aspect:6.3f} "
            f"| {x_mm:7.2f} {y_mm:7.2f} {d_mm:8.2f}"
        )

        # Draw cyan fitted circle right over your red circle for visual confirmation
        cv2.circle(vis, (int(round(cx)), int(round(cy))), int(round(r)), (255, 255, 0), 1)
        cv2.circle(vis, (int(round(cx)), int(round(cy))), 3, (255, 255, 0), -1)
        cv2.putText(vis, f"H{i+1}", (int(cx - r), max(22, int(cy - r - 6))),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)

    cv2.imwrite(OUT_IMG_PATH, vis)

    # Export 3D OpenSCAD file
    y_min = min(h_[2] for h_ in cad_holes) - 10.0
    y_max = max(h_[2] for h_ in cad_holes) + 10.0
    plate_len = y_max - y_min
    plate_cy = 0.5 * (y_min + y_max)

    with open(OUT_SCAD_PATH, "w") as f:
        f.write("// Fitted from manual red circles + camera-angle correction\n")
        f.write("$fn = 64;\n")
        f.write(f"plate_w = {EST_PLATE_WIDTH_MM:.2f};\n")
        f.write(f"plate_l = {plate_len:.2f};\n")
        f.write(f"thickness = {EST_THICKNESS_MM:.2f};\n\n")
        f.write("difference() {\n")
        f.write(f"  translate([0, {-plate_cy:.2f}, thickness/2])\n")
        f.write("    cube([plate_w, plate_l, thickness], center=true);\n")
        for name, xm, ym, dm in cad_holes:
            f.write(f"  // {name}\n")
            f.write(f"  translate([{xm:.2f}, {-ym:.2f}, -0.5]) cylinder(d={dm:.2f}, h=thickness+1);\n")
        f.write("}\n")
    print(f"\nSaved: {OUT_IMG_PATH} and {OUT_SCAD_PATH}")


if __name__ == "__main__":
    main()