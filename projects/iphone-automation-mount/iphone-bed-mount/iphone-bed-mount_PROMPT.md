# Fusion 360 Python Prompt: Prusa Mini iPhone Mount

Write an Autodesk Fusion 360 Python API script that builds a 3D-printable bed mount for a Prusa Mini to hold an iPhone SE (2nd gen) for timelapses. 

Model the part as a single solid body using a standard human modeling sequence:

---

### 1. Bed Attachment & Side Arm
- **Rear Mount Bar:** Sits along the back edge of the bed and hooks directly onto the Prusa Mini's two rear bed alignment pins. Round off the outer ends so there are no sharp edges.
- **Connecting Arm:** Runs forward along the right side of the bed to hold the phone cradle. 
- **Strength & Weight:** 
  - Add a smooth, generous curve where the arm meets the rear mount bar so the joint does not snap under vibration.
  - Cut a long slot with rounded ends down the center of the arm to cut down on print time and weight while keeping it stiff.
  - Trim a notch out of the front-right corner so the printhead has plenty of room to home safely.

---

### 2. Phone Cradle & Walls
- **Phone Pocket:** Sits flat on the bed, holding the iPhone SE 2 horizontally with the screen facing up. Make the pocket just slightly larger than the phone so it slides in easily.
- **Retaining Walls:** Extrude walls around the perimeter just tall enough to secure the phone without covering the screen. Keep the inside corner between the cradle and arm a clean right angle.

---

### 3. Wall Openings
Cut through the walls down to the floor so the cradle never accidentally presses any buttons:
- **Bottom edge (left wall):** Opening for the Lightning charging cable.
- **Right edge of phone (front wall):** Cutout positioned to clear the power/wake button.
- **Left edge of phone (rear wall):** A wide opening that clears both volume buttons and the mute switch together.

---

### 4. Base Floor Pattern
- **Camera Window:** Cut a neat, compact square window in the corner directly under the rear camera and flash so the lens has an unobstructed view downward.
- **Filament-Saving Grid:** Fill the rest of the pocket floor with an alternating checkerboard pattern of rounded cutouts (open-solid-open across the back row). Leave a solid border around the edges and solid cross-ribs for bed adhesion and rigidity. Automatically skip any grid hole that runs into the camera window.

---

### 5. Script Details
- Wrap the code in a standard `run(context)` function with a `try/except` block.
- Name the final body `"Prusa_Mini_iPhone_SideArm_Mount"`.
- Show a simple message box at the end confirming the mount was created.