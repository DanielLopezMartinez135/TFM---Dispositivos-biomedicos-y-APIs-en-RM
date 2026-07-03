using UnityEngine;
using UnityEditor;
using UnityEditor.Events;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using TMPro;

namespace VitalsVR
{
    public class VRSceneSetup : EditorWindow
    {
        [MenuItem("Vitals VR/Setup VR Scene")]
        public static void CreateVRScene()
        {
            // 1. Create EventSystem if not present
            if (FindObjectOfType<EventSystem>() == null)
            {
                GameObject eventSystem = new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
                Undo.RegisterCreatedObjectUndo(eventSystem, "Create Event System");
            }

            // 2. Create Camera if not present
            Camera mainCam = Camera.main;
            if (mainCam == null)
            {
                GameObject camObj = new GameObject("Main Camera", typeof(Camera), typeof(AudioListener));
                camObj.tag = "MainCamera";
                camObj.transform.position = new Vector3(0, 1.6f, 0);
                mainCam = camObj.GetComponent<Camera>();
                Undo.RegisterCreatedObjectUndo(camObj, "Create Main Camera");
            }
            
            if (mainCam.transform.position == Vector3.zero)
            {
                mainCam.transform.position = new Vector3(0, 1.6f, 0);
            }

            // 3. Create main HUD Canvas (World Space)
            // NOTE: No background Image is attached here to keep the rest of the canvas 
            // transparent for Augmented Reality (AR) pass-through views.
            GameObject canvasObj = new GameObject("VitalsVR_Canvas", typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            canvasObj.transform.position = new Vector3(0, 1.5f, 2.0f);
            canvasObj.transform.rotation = Quaternion.identity;
            
            Canvas canvas = canvasObj.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.WorldSpace;
            
            CanvasScaler scaler = canvasObj.GetComponent<CanvasScaler>();
            scaler.dynamicPixelsPerUnit = 10;
            
            RectTransform canvasRect = canvasObj.GetComponent<RectTransform>();
            canvasRect.sizeDelta = new Vector2(960, 680);
            canvasRect.localScale = new Vector3(0.002f, 0.002f, 0.002f); // Scale down for VR/AR comfortable size

            canvasObj.AddComponent<Billboard>();

            // Attach core scripts
            MetricsFetcher fetcher = canvasObj.AddComponent<MetricsFetcher>();
            MetricsDisplay display = canvasObj.AddComponent<MetricsDisplay>();
            VRHUDManager hudManager = canvasObj.AddComponent<VRHUDManager>();

            // --- PART 1: TOGGLE SETTINGS BUTTON (BOTTOM RIGHT) ---
            GameObject toggleBtnObj = CreateButton(canvasObj.transform, "SettingsToggleButton", "Login Settings", new Color(0.12f, 0.16f, 0.24f, 0.75f), 140);
            RectTransform toggleRect = toggleBtnObj.GetComponent<RectTransform>();
            toggleRect.anchorMin = new Vector2(1, 0);
            toggleRect.anchorMax = new Vector2(1, 0);
            toggleRect.pivot = new Vector2(1, 0);
            toggleRect.anchoredPosition = new Vector2(-40, 40); // Float at bottom-right
            Button toggleBtn = toggleBtnObj.GetComponent<Button>();

            // --- PART 2: LOGIN DIALOG WINDOW (CENTERED) ---
            GameObject loginPanelObj = new GameObject("LoginPanel", typeof(RectTransform), typeof(Image));
            loginPanelObj.transform.SetParent(canvasObj.transform, false);
            loginPanelObj.GetComponent<Image>().color = new Color(0.08f, 0.10f, 0.15f, 0.92f); // Dark, high-contrast overlay
            
            RectTransform loginPanelRect = loginPanelObj.GetComponent<RectTransform>();
            loginPanelRect.anchorMin = new Vector2(0.5f, 0.5f);
            loginPanelRect.anchorMax = new Vector2(0.5f, 0.5f);
            loginPanelRect.pivot = new Vector2(0.5f, 0.5f);
            loginPanelRect.sizeDelta = new Vector2(500, 310);

            // Vertical Layout for login fields
            VerticalLayoutGroup loginLayout = loginPanelObj.AddComponent<VerticalLayoutGroup>();
            loginLayout.padding = new RectOffset(25, 25, 20, 20);
            loginLayout.spacing = 10;
            loginLayout.childAlignment = TextAnchor.UpperCenter;
            loginLayout.childControlHeight = false;
            loginLayout.childControlWidth = true;
            loginLayout.childForceExpandHeight = false;
            loginLayout.childForceExpandWidth = true;

            // Title inside login panel
            GameObject loginTitleObj = new GameObject("LoginTitle", typeof(RectTransform));
            loginTitleObj.transform.SetParent(loginPanelObj.transform, false);
            TextMeshProUGUI loginTitleText = loginTitleObj.AddComponent<TextMeshProUGUI>();
            loginTitleText.text = "VITALS API CONNECTION";
            loginTitleText.fontSize = 18;
            loginTitleText.fontStyle = FontStyles.Bold;
            loginTitleText.alignment = TextAlignmentOptions.Center;
            loginTitleText.color = new Color(0.2f, 0.7f, 1.0f);
            loginTitleObj.GetComponent<RectTransform>().sizeDelta = new Vector2(450, 25);

            // Credentials Input fields (URLs, Username, Password)
            GameObject urlInputObj = CreateInputField(loginPanelObj.transform, "URLInput", "API URL (e.g. http://localhost:8000)", 450);
            TMP_InputField urlInput = urlInputObj.GetComponent<TMP_InputField>();

            GameObject userInputObj = CreateInputField(loginPanelObj.transform, "UserInput", "Username", 450);
            TMP_InputField userInput = userInputObj.GetComponent<TMP_InputField>();

            GameObject passInputObj = CreateInputField(loginPanelObj.transform, "PassInput", "Password", 450);
            TMP_InputField passInput = passInputObj.GetComponent<TMP_InputField>();
            passInput.contentType = TMP_InputField.ContentType.Password;

            // Connect button inside login panel
            GameObject connectBtnObj = CreateButton(loginPanelObj.transform, "ConnectButton", "Connect to Server", new Color(0.15f, 0.5f, 0.85f), 450);
            Button connectBtn = connectBtnObj.GetComponent<Button>();

            // Status message field inside login panel
            GameObject statusObj = new GameObject("StatusText", typeof(RectTransform));
            statusObj.transform.SetParent(loginPanelObj.transform, false);
            TextMeshProUGUI statusText = statusObj.AddComponent<TextMeshProUGUI>();
            statusText.text = "Enter credentials to fetch live patient metrics.";
            statusText.fontSize = 13;
            statusText.alignment = TextAlignmentOptions.Center;
            statusText.color = Color.white;
            statusObj.GetComponent<RectTransform>().sizeDelta = new Vector2(450, 20);


            // --- PART 3: LIVE METRICS HUD (LEFT SIDE) ---
            GameObject hudPanelObj = new GameObject("MetricsHUDPanel", typeof(RectTransform), typeof(Image));
            hudPanelObj.transform.SetParent(canvasObj.transform, false);
            // Semi-transparent AR-friendly background panel (45% opacity)
            hudPanelObj.GetComponent<Image>().color = new Color(0.06f, 0.08f, 0.12f, 0.45f);

            RectTransform hudPanelRect = hudPanelObj.GetComponent<RectTransform>();
            hudPanelRect.anchorMin = new Vector2(0, 0.5f);
            hudPanelRect.anchorMax = new Vector2(0, 0.5f);
            hudPanelRect.pivot = new Vector2(0, 0.5f);
            hudPanelRect.sizeDelta = new Vector2(420, 600);
            hudPanelRect.anchoredPosition = new Vector2(40, 0); // Side placement

            // Vertical Layout for HUD contents
            VerticalLayoutGroup hudLayout = hudPanelObj.AddComponent<VerticalLayoutGroup>();
            hudLayout.padding = new RectOffset(20, 20, 20, 20);
            hudLayout.spacing = 15;
            hudLayout.childAlignment = TextAnchor.UpperCenter;
            hudLayout.childControlHeight = true;
            hudLayout.childControlWidth = true;
            hudLayout.childForceExpandHeight = false;
            hudLayout.childForceExpandWidth = true;

            // HUD Title Block (Horizontal: Title + Refresh Icon button)
            GameObject hudHeaderObj = new GameObject("HUDHeader", typeof(RectTransform));
            hudHeaderObj.transform.SetParent(hudPanelObj.transform, false);
            HorizontalLayoutGroup hudHeaderLayout = hudHeaderObj.AddComponent<HorizontalLayoutGroup>();
            hudHeaderLayout.childControlWidth = true;
            hudHeaderLayout.childForceExpandWidth = false;
            hudHeaderObj.GetComponent<RectTransform>().sizeDelta = new Vector2(380, 40);

            GameObject hudTitleObj = new GameObject("HUDTitleText", typeof(RectTransform));
            hudTitleObj.transform.SetParent(hudHeaderObj.transform, false);
            TextMeshProUGUI hudTitleText = hudTitleObj.AddComponent<TextMeshProUGUI>();
            hudTitleText.text = "PATIENT METRICS";
            hudTitleText.fontSize = 22;
            hudTitleText.alignment = TextAlignmentOptions.Left;
            hudTitleText.fontStyle = FontStyles.Bold;
            hudTitleText.color = new Color(0.2f, 0.75f, 1.0f);

            // Small refresh button on the HUD itself
            GameObject hudRefreshBtnObj = CreateButton(hudHeaderObj.transform, "HUDRefreshButton", "Refresh", new Color(0.15f, 0.65f, 0.35f), 80);
            Button hudRefreshBtn = hudRefreshBtnObj.GetComponent<Button>();

            // Live Metrics Scroll View
            GameObject scrollViewObj = new GameObject("MetricsScrollView", typeof(RectTransform), typeof(ScrollRect));
            scrollViewObj.transform.SetParent(hudPanelObj.transform, false);
            LayoutElement scrollLayoutElement = scrollViewObj.AddComponent<LayoutElement>();
            scrollLayoutElement.preferredHeight = 480f;
            scrollLayoutElement.minHeight = 200f;
            scrollLayoutElement.flexibleHeight = 1f;

            ScrollRect sRect = scrollViewObj.GetComponent<ScrollRect>();
            sRect.horizontal = false;
            sRect.vertical = true;
            sRect.movementType = ScrollRect.MovementType.Clamped;

            // Viewport with RectMask2D clipping
            GameObject viewportObj = new GameObject("Viewport", typeof(RectTransform), typeof(RectMask2D));
            viewportObj.transform.SetParent(scrollViewObj.transform, false);
            
            RectTransform viewRect = viewportObj.GetComponent<RectTransform>();
            viewRect.anchorMin = Vector2.zero;
            viewRect.anchorMax = Vector2.one;
            viewRect.sizeDelta = Vector2.zero;
            sRect.viewport = viewRect;

            // Scroll View Content Container
            GameObject contentObj = new GameObject("Content", typeof(RectTransform));
            contentObj.transform.SetParent(viewportObj.transform, false);
            
            RectTransform contentRect = contentObj.GetComponent<RectTransform>();
            contentRect.anchorMin = new Vector2(0, 1);
            contentRect.anchorMax = new Vector2(1, 1);
            contentRect.pivot = new Vector2(0.5f, 1);
            contentRect.sizeDelta = new Vector2(0, 300);
            sRect.content = contentRect;

            VerticalLayoutGroup contentLayout = contentObj.AddComponent<VerticalLayoutGroup>();
            contentLayout.padding = new RectOffset(5, 5, 5, 5);
            contentLayout.spacing = 12;
            contentLayout.childAlignment = TextAnchor.UpperCenter;
            contentLayout.childControlHeight = false;
            contentLayout.childControlWidth = true;
            contentLayout.childForceExpandHeight = false;
            contentLayout.childForceExpandWidth = true;

            ContentSizeFitter fitter = contentObj.AddComponent<ContentSizeFitter>();
            fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;


            // --- WIRE SCRIPTS AND REFERENCES ---
            display.fetcher = fetcher;
            display.statusText = statusText;
            display.cardContainer = contentRect;
            display.usernameInput = userInput;
            display.passwordInput = passInput;
            display.urlInput = urlInput;

            hudManager.fetcher = fetcher;
            hudManager.loginPanel = loginPanelObj;
            hudManager.metricsHUDPanel = hudPanelObj;
            hudManager.loginToggleButton = toggleBtnObj;

            // Wire persistent listeners to serialize buttons in the Unity scene file
            UnityEventTools.AddPersistentListener(toggleBtn.onClick, hudManager.ToggleLoginPanel);
            UnityEventTools.AddPersistentListener(connectBtn.onClick, display.OnLoginButtonClicked);
            UnityEventTools.AddPersistentListener(hudRefreshBtn.onClick, display.OnRefreshButtonClicked);

            // Automatically select new Canvas
            Selection.activeGameObject = canvasObj;
            Undo.RegisterCreatedObjectUndo(canvasObj, "Setup VR/AR HUD Canvas");

            UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());

            Debug.Log("VR/AR HUD split UI successfully created and wired.");
        }

        private static GameObject CreateInputField(Transform parent, string name, string placeholderText, float width)
        {
            GameObject inputObj = new GameObject(name, typeof(RectTransform), typeof(Image));
            inputObj.transform.SetParent(parent, false);
            inputObj.GetComponent<Image>().color = new Color(0.2f, 0.25f, 0.35f, 0.85f);

            RectTransform rect = inputObj.GetComponent<RectTransform>();
            rect.sizeDelta = new Vector2(width, 36);

            GameObject textObj = new GameObject("Text", typeof(RectTransform));
            textObj.transform.SetParent(inputObj.transform, false);
            TextMeshProUGUI text = textObj.AddComponent<TextMeshProUGUI>();
            text.fontSize = 14;
            text.color = Color.white;
            text.verticalAlignment = VerticalAlignmentOptions.Middle;

            RectTransform textRect = textObj.GetComponent<RectTransform>();
            textRect.anchorMin = Vector2.zero;
            textRect.anchorMax = Vector2.one;
            textRect.sizeDelta = new Vector2(-16, -8);
            textRect.anchoredPosition = Vector2.zero;

            GameObject placeholderObj = new GameObject("Placeholder", typeof(RectTransform));
            placeholderObj.transform.SetParent(inputObj.transform, false);
            TextMeshProUGUI placeholder = placeholderObj.AddComponent<TextMeshProUGUI>();
            placeholder.text = placeholderText;
            placeholder.fontSize = 14;
            placeholder.fontStyle = FontStyles.Italic;
            placeholder.color = new Color(0.6f, 0.65f, 0.7f);
            placeholder.verticalAlignment = VerticalAlignmentOptions.Middle;

            RectTransform placeholderRect = placeholderObj.GetComponent<RectTransform>();
            placeholderRect.anchorMin = Vector2.zero;
            placeholderRect.anchorMax = Vector2.one;
            placeholderRect.sizeDelta = new Vector2(-16, -8);
            placeholderRect.anchoredPosition = Vector2.zero;

            TMP_InputField inputField = inputObj.AddComponent<TMP_InputField>();
            inputField.textComponent = text;
            inputField.placeholder = placeholder;
            inputField.textViewport = textRect;

            return inputObj;
        }

        private static GameObject CreateButton(Transform parent, string name, string labelText, Color color, float width)
        {
            GameObject btnObj = new GameObject(name, typeof(RectTransform), typeof(Image), typeof(Button));
            btnObj.transform.SetParent(parent, false);
            btnObj.GetComponent<Image>().color = color;

            RectTransform rect = btnObj.GetComponent<RectTransform>();
            rect.sizeDelta = new Vector2(width, 36);

            GameObject textObj = new GameObject("Text", typeof(RectTransform));
            textObj.transform.SetParent(btnObj.transform, false);
            TextMeshProUGUI text = textObj.AddComponent<TextMeshProUGUI>();
            text.text = labelText;
            text.fontSize = 14;
            text.alignment = TextAlignmentOptions.Center;
            text.fontStyle = FontStyles.Bold;
            text.color = Color.white;

            RectTransform textRect = textObj.GetComponent<RectTransform>();
            textRect.anchorMin = Vector2.zero;
            textRect.anchorMax = Vector2.one;
            textRect.sizeDelta = Vector2.zero;
            textRect.anchoredPosition = Vector2.zero;

            Button btn = btnObj.GetComponent<Button>();
            btn.targetGraphic = btnObj.GetComponent<Image>();
            
            ColorBlock cb = btn.colors;
            cb.normalColor = color;
            cb.highlightedColor = color * 1.15f;
            cb.pressedColor = color * 0.85f;
            btn.colors = cb;

            return btnObj;
        }
    }
}
