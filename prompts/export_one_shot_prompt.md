# Fusion 360 Python Prompt Generator

Given a project or design description, create a clear, complete prompt that will guide an AI to generate a Fusion 360 Python API script for the whole design.

1. **Use Fusion 360 Python scripts.** The generated prompt must ask for a script that creates the requested project or design in Autodesk Fusion 360 using its Python API.
2. **Model the human way, with fewer numbers.** Ask for a simple, understandable feature sequence using familiar Fusion 360 tools. Include only dimensions needed to define the design; do not invent details or add unnecessary coordinates, parameters, or complexity.

Consider the full project or design as a whole, including its purpose, parts, relationships, and supplied requirements. Preserve provided details, and make any important missing information or assumptions clear in the generated prompt. Output the prompt, not the Fusion 360 script.

Export a plain markdown file, and format the markdown file.
