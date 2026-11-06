# Design Prompt: Prusa Mini Hotend Stylus Holder (Standard Mount)

### 1. Goal
Design a 3D-printable mounting bracket that attaches to the heatsink of a Prusa Mini 3D printer to hold a touchscreen stylus pen. This allows the 3D printer to be used as an automated test rig for tapping and swiping on an iPhone screen.

### 2. Mounting Interface (Prusa Mini Heatsink)
- Attaches to the heatsink using **two diagonal M3 mounting screws**.
- The two screw holes need **wide counterbores** from the top face so standard socket-head cap screws sit countersunk below the surface.
- The base plate should have rounded lobes around both screw holes and smooth fillet transitions connecting them into a clean, rigid bracket.

### 3. Stylus Clamp Block
- Integrated directly along the side of the base plate.
- The block features an **arch-shaped rounded crown** on top.
- Cut a **7.3 mm horizontal through-bore** through the block to snugly hold a standard capacitive stylus pen.
- Add an **M3 clearance hole from the bottom** into the stylus bore to lock the pen in place with a set screw.
- Add a small round positioning boss on the top side of the block.

### 4. 3D Printability & Requirements
- **Overall plate thickness:** ~4 mm for rigidity.
- **Flat bottom:** Oriented flat on the XY plane for easy FDM 3D printing without needing support material.
- Write clean, native Fusion 360 Python API code that builds the part parametrically from sketches and extrusions.