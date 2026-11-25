import adsk.core
import adsk.fusion
import traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        docs = app.documents
        doc_count = docs.count
        
        # 1. Close all currently open documents without saving
        if doc_count > 0:
            closed_count = 0
            while docs.count > 0:
                doc = docs.item(0)
                doc.close(False)  # False forces closure, discarding unsaved edits
                closed_count += 1
        
        # 2. Search for "ai stylus holder" across all available cloud hubs and projects
        data = app.data
        target_file_name = "ai stylus holder"
        target_file = None
        
        # Safely loop through hubs and projects to avoid activeProject validation errors
        for hub in data.dataHubs:
            for project in hub.dataProjects:
                root_folder = project.rootFolder
                
                # Check files in root folder
                for file in root_folder.dataFiles:
                    if target_file_name.lower() in file.name.lower():
                        target_file = file
                        break
                if target_file:
                    break
                    
                # Check files in immediate subfolders
                for folder in root_folder.dataFolders:
                    for file in folder.dataFiles:
                        if target_file_name.lower() in file.name.lower():
                            target_file = file
                            break
                    if target_file:
                        break
                if target_file:
                    break
            if target_file:
                break
                
        # 3. Open the file from the cloud if found
        if target_file:
            app.documents.open(target_file)
        else:
            ui.messageBox(f"Closed {doc_count} file(s), but could not find '{target_file_name}' in your cloud projects. Check the file name.")
            
    except Exception as e:
        if ui:
            ui.messageBox(f'Script execution failed:\n{traceback.format_exc()}')

def stop(context):
    pass