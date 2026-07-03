# Vitals VR/AR Telemetry Integration Plugin

A modular, self-contained Unity Package Manager (UPM) local package that enables real-time patient biomedical telemetry visualization in VR and AR environments.

---

## 📦 Package Contents

- **`Runtime/`**: Contains core logic, fetchers, and UI display components.
  - `Scripts/MetricsData.cs`: Serializable JSON payload structures.
  - `Scripts/MetricsFetcher.cs`: Handles login/authentication token retrieval and API calls.
  - `Scripts/MetricsDisplay.cs`: Dynamic programmatical creation of metric visual cards.
  - `Scripts/Billboard.cs`: Directs the overlay canvas to face the camera.
  - `Scripts/VRHUDManager.cs`: Controls UI transitions (login toggle, auto-hide on metrics fetch).
  - `VitalsVR.Runtime.asmdef`: Assembly definition compiling these scripts into `VitalsVR.Runtime.dll`.
- **`Editor/`**: Includes custom editor extensions.
  - `VRSceneSetup.cs`: Automated builder that configures the entire canvas hierarchy.
  - `VitalsVR.Editor.asmdef`: Editor-only assembly definition compiling these scripts into `VitalsVR.Editor.dll`.

---

## 🔌 Installing in another Unity Project

Because this is organized as a standard UPM Package, you can install it in any other project in two ways:

### Method A: Local Folder Copy (Easiest)
1. Copy the `com.vitals.vr` folder.
2. Open your destination Unity project directory, navigate to its `Packages/` folder, and paste the `com.vitals.vr` folder there.
3. Open Unity. It will automatically detect, compile, and add the plugin.

### Method B: Adding via Package Manager (Local Reference)
1. Keep the `com.vitals.vr` folder in its current path.
2. In your target Unity project, select **Window** -> **Package Manager**.
3. Click the **+** (add) button at the top left, and choose **Add package from disk...**.
4. Navigate to this folder and select the `package.json` file.
5. Unity will create a local symbolic link to the package.

---

## 🚀 Usage

1. Open a new scene.
2. Go to **Vitals VR** -> **Setup VR Scene** in the top menu.
3. The script will generate a complete Canvas hierarchy in front of your Main Camera:
   - **SettingsToggleButton (Bottom Right)**: Always visible. Toggles credentials panel.
   - **LoginPanel (Centered)**: Opens to configure API endpoints and password logins. Auto-hides upon success.
   - **MetricsHUDPanel (Left Side)**: Semi-transparent overlay displaying live metrics (AR passthrough-friendly). Includes a manual **Refresh** button inside the HUD header.
4. Fill in connection details in the `VitalsVR_Canvas` inspector and hit **Play**!
