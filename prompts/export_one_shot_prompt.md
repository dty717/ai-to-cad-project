# Fusion 360 One-Shot Requirement Exporter

Review our entire conversation and any generated code, then distill the final design into a single, clean prompt so a new AI can build the complete Fusion 360 Python script in **one talk**.

### Rules for Exporting the Requirement:
1. **Strip Code & Coordinate Numbers:** Do NOT copy raw coordinates, `Point3D` values, or low-level API numbers from our previous code. Ignore failed attempts and intermediate tweaks—export only the final intended design.
2. **Keep Only Key Driving Dimensions:** Include only the essential overall dimensions needed to define the part (typically 3–8 key numbers, such as overall length, width, height, wall thickness, or main hole size). 
3. **Use Relationships Instead of Numbers:** Replace secondary numbers and positions with geometric relationships (e.g., "centered on the origin", "symmetric", "evenly spaced", "flush with the top face", "offset by wall thickness").
4. **Describe the Human CAD Workflow:** Outline the design as a simple, logical sequence of familiar Fusion 360 features (e.g., Base Sketch → Extrude → Shell → Cut Hole → Pattern → Fillet) rather than low-level geometry math.
5. **Target Output:** The exported prompt must instruct the new AI to write a clean, parametric Fusion 360 Python API script using top-level variables for the key dimensions.

Output **only** the final one-shot prompt, ready to copy and paste into a new chat.
