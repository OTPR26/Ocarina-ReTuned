    if(RetunedFrontend::MobileSettingsPlatform()) {
        bool changed=RetunedFrontend::Toggle("Use custom textures",&settings.LoadCustomTextures);
        auto& folders=RetunedFrontend::TextureFolders;
        if(folders.TakeSelection){
            const auto selected=folders.TakeSelection();
            if(!selected.empty()){settings.LoadDirectory=selected;settings.LoadCustomTextures=true;changed=true;}
        }
        if(folders.Choose && ImGui::Button("Choose texture folder"))folders.Choose();
        if(folders.Status){const auto message=folders.Status();if(!message.empty())ImGui::TextWrapped("%s",message.c_str());}
        ImGui::TextWrapped("Searches the selected folder and all subfolders. You can change it before or during gameplay.");
        auto& packs=::Oot3d::Renderer::AzaharTexturePackRuntime::Instance();
        if(ImGui::Button("Reload textures"))packs.Reload();
        const auto status=packs.Snapshot();
        if(status.IndexPending)ImGui::TextWrapped("Finding textures...");
        else if(status.IndexedTextures==0)ImGui::TextWrapped(folders.Choose?"No textures found. Choose a texture folder.":"No texture pack found.");
        else ImGui::TextWrapped("%zu textures available; %zu loaded",status.IndexedTextures,status.LoadedTextures);
        if(status.PendingLoads)ImGui::Text("Loading: %zu",status.PendingLoads);
        if(status.FailedLoads)ImGui::Text("Could not load: %zu",status.FailedLoads);
        if(!status.LastError.empty())ImGui::TextWrapped("%s",status.LastError.c_str());
        return changed;
    }
