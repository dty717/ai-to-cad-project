# 🖊️ Prusa Mini Heatsink Stylus Holder Mod

Parametric Fusion 360 generator for mounting a capacitive stylus pen to the Prusa Mini/Mini+ printhead for automated screen testing.

---

## 📌 Variations Included

| Script | Offset along X | Purpose |
| :--- | :--- | :--- |
| **`stylus_holder_standard.py`** | $0\text{ mm}$ (Direct mount) | Compact mounting directly adjacent to the heatsink. |
| **`stylus_holder_offset_65mm.py`** | **$+65\text{ mm}$ Cantilever Arm** | Extends the stylus forward/rightward to align directly over an iPhone held in the [`iphone-bed-mount`](../iphone-bed-mount/). |

---

## ⚙️ Mechanical Specifications

* **Mounting Pattern:** Fixed dual M3 holes at `(16.0, 16.0)` and `(-16.0, -16.0)` mm with $\varnothing 12\text{ mm}$ counterbore recesses for socket-head cap screws.
* **Stylus Bore Diameter:** $\varnothing 7.3\text{ mm}$ with a radiused upper crown, sized for standard rubber/mesh capacitive stylus pens.
* **Retention Hardware:**
  * Top Boss: $\varnothing 6.0\text{ mm}$ boss ($+2.5\text{ mm}$ protrusion).
  * Bottom Lock Hole: $\varnothing 3.4\text{ mm}$ hole for an M3 set/clamping screw.
* **Base Plate Thickness:** $4.0\text{ mm}$ rigid foundation.

---

## 🚀 How to Run

1. Open Fusion 360.
2. Press `Shift + S`.
3. Choose either `stylus_holder_offset_65mm.py` (recommended for use with the iPhone bed fixture) or `stylus_holder_standard.py`.
4. Click **Run**.
5. Export as `.step` or `.stl` and slice with $3+$ perimeters in PETG.
