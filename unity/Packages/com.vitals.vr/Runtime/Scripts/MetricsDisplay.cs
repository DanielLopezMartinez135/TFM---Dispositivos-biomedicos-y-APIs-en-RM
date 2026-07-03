using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

namespace VitalsVR
{
    public class MetricsDisplay : MonoBehaviour
    {
        [Header("Backend Reference")]
        public MetricsFetcher fetcher;

        [Header("UI Fields")]
        public TextMeshProUGUI statusText;
        public Transform cardContainer;
        public TMP_InputField usernameInput;
        public TMP_InputField passwordInput;
        public TMP_InputField urlInput;

        [Header("Card Customization")]
        [Tooltip("Optional card prefab. If empty, cards will be generated programmatically with beautiful dark glass styling.")]
        public GameObject cardPrefab;

        private void Start()
        {
            if (fetcher == null)
                fetcher = GetComponent<MetricsFetcher>();

            if (fetcher != null)
            {
                fetcher.OnMetricsReceived += UpdateMetricsUI;
                fetcher.OnStatusChanged += UpdateStatus;
                
                if (usernameInput != null) usernameInput.text = fetcher.username;
                if (passwordInput != null) passwordInput.text = fetcher.password;
                if (urlInput != null) urlInput.text = fetcher.apiBaseUrl;
                
                fetcher.FetchMetrics();
            }
        }

        private void OnDestroy()
        {
            if (fetcher != null)
            {
                fetcher.OnMetricsReceived -= UpdateMetricsUI;
                fetcher.OnStatusChanged -= UpdateStatus;
            }
        }

        public void OnLoginButtonClicked()
        {
            if (fetcher != null)
            {
                if (usernameInput != null) fetcher.username = usernameInput.text;
                if (passwordInput != null) fetcher.password = passwordInput.text;
                if (urlInput != null) fetcher.apiBaseUrl = urlInput.text;
                
                fetcher.FetchMetrics();
            }
        }

        public void OnRefreshButtonClicked()
        {
            if (fetcher != null)
            {
                fetcher.FetchMetrics();
            }
        }

        private void UpdateStatus(string message, bool isError)
        {
            if (statusText != null)
            {
                statusText.text = message;
                statusText.color = isError ? new Color(1f, 0.4f, 0.4f) : new Color(0.2f, 0.85f, 0.4f);
            }
        }

        private void UpdateMetricsUI(List<MetricItem> metrics)
        {
            foreach (Transform child in cardContainer)
            {
                Destroy(child.gameObject);
            }

            if (metrics == null || metrics.Count == 0)
            {
                CreateNoMetricsCard();
                return;
            }

            foreach (var metric in metrics)
            {
                CreateMetricCard(metric);
            }
        }

        private void CreateNoMetricsCard()
        {
            GameObject cardObj = new GameObject("NoMetricsMessage", typeof(RectTransform));
            cardObj.transform.SetParent(cardContainer, false);
            
            TextMeshProUGUI text = cardObj.AddComponent<TextMeshProUGUI>();
            text.text = "No metrics found. Please verify your Withings / device connection on the dashboard.";
            text.alignment = TextAlignmentOptions.Center;
            text.fontSize = 16;
            text.color = new Color(0.7f, 0.7f, 0.7f);
            
            RectTransform rect = cardObj.GetComponent<RectTransform>();
            rect.sizeDelta = new Vector2(500, 60);
        }

        private void CreateMetricCard(MetricItem metric)
        {
            if (cardPrefab != null)
            {
                GameObject card = Instantiate(cardPrefab, cardContainer);
                return;
            }

            GameObject cardObj = new GameObject($"Card_{metric.metric}", typeof(RectTransform), typeof(Image));
            cardObj.transform.SetParent(cardContainer, false);
            
            RectTransform rect = cardObj.GetComponent<RectTransform>();
            rect.sizeDelta = new Vector2(760, 110);
            
            // Sleek translucent background panel (45% opacity for AR blend)
            Image bgImage = cardObj.GetComponent<Image>();
            bgImage.color = new Color(0.12f, 0.16f, 0.24f, 0.45f);

            VerticalLayoutGroup vLayout = cardObj.AddComponent<VerticalLayoutGroup>();
            vLayout.padding = new RectOffset(20, 20, 12, 12);
            vLayout.spacing = 6;
            vLayout.childAlignment = TextAnchor.UpperLeft;
            vLayout.childControlHeight = true;
            vLayout.childControlWidth = true;
            vLayout.childForceExpandHeight = false;
            vLayout.childForceExpandWidth = true;

            // Row 1: Title and Provider Name
            GameObject headerObj = new GameObject("HeaderRow", typeof(RectTransform));
            headerObj.transform.SetParent(cardObj.transform, false);
            HorizontalLayoutGroup hLayout = headerObj.AddComponent<HorizontalLayoutGroup>();
            hLayout.childControlWidth = true;
            hLayout.childForceExpandWidth = false;

            GameObject titleObj = new GameObject("TitleText", typeof(RectTransform));
            titleObj.transform.SetParent(headerObj.transform, false);
            TextMeshProUGUI titleText = titleObj.AddComponent<TextMeshProUGUI>();
            titleText.text = FormatMetricName(metric.metric);
            titleText.fontSize = 18;
            titleText.fontStyle = FontStyles.Bold;
            titleText.color = Color.white;

            GameObject providerObj = new GameObject("ProviderText", typeof(RectTransform));
            providerObj.transform.SetParent(headerObj.transform, false);
            TextMeshProUGUI providerText = providerObj.AddComponent<TextMeshProUGUI>();
            providerText.text = metric.provider.ToUpper();
            providerText.fontSize = 12;
            providerText.fontStyle = FontStyles.Bold;
            providerText.alignment = TextAlignmentOptions.Right;
            providerText.color = new Color(0.2f, 0.7f, 1.0f); // Accent blue

            // Row 2: Large Value & Unit
            GameObject valueObj = new GameObject("ValueText", typeof(RectTransform));
            valueObj.transform.SetParent(cardObj.transform, false);
            TextMeshProUGUI valueText = valueObj.AddComponent<TextMeshProUGUI>();
            valueText.text = $"{metric.value:F1} <size=70%>{metric.unit}</size>";
            valueText.fontSize = 32;
            valueText.fontStyle = FontStyles.Bold;
            valueText.color = GetMetricColor(metric.metric);

            // Row 3: Metadata (Device description and date)
            GameObject metaObj = new GameObject("MetadataText", typeof(RectTransform));
            metaObj.transform.SetParent(cardObj.transform, false);
            TextMeshProUGUI metaText = metaObj.AddComponent<TextMeshProUGUI>();
            
            string formattedDate = metric.measurement_date;
            if (System.DateTime.TryParse(metric.measurement_date, out System.DateTime dt))
            {
                formattedDate = dt.ToString("yyyy-MM-dd HH:mm");
            }
            
            metaText.text = $"{metric.device}  •  {formattedDate}";
            metaText.fontSize = 12;
            metaText.color = new Color(0.6f, 0.65f, 0.7f);
        }

        private string FormatMetricName(string name)
        {
            if (string.IsNullOrEmpty(name)) return "";
            
            string lowerName = name.ToLower().Replace('_', ' ').Trim();
            switch (lowerName)
            {
                case "peso":
                    return "Weight";
                case "frecuencia cardiaca":
                case "frecuencia_cardiaca":
                case "pulso":
                    return "Heart Rate";
                case "presion sistolica":
                case "presion_sistolica":
                    return "Systolic Pressure";
                case "presion diastolica":
                case "presion_diastolica":
                    return "Diastolic Pressure";
                default:
                    name = name.Replace('_', ' ');
                    return char.ToUpper(name[0]) + name.Substring(1);
            }
        }

        private Color GetMetricColor(string metric)
        {
            if (string.IsNullOrEmpty(metric)) return Color.white;

            string lowerMetric = metric.ToLower().Replace('_', ' ').Trim();
            switch (lowerMetric)
            {
                case "peso":
                case "weight":
                    return new Color(0.3f, 0.8f, 1f); // Cyan
                case "frecuencia cardiaca":
                case "frecuencia_cardiaca":
                case "heart rate":
                case "pulse":
                    return new Color(1f, 0.35f, 0.45f); // Coral Red
                case "presion sistolica":
                case "presion_sistolica":
                case "presion diastolica":
                case "presion_diastolica":
                case "blood pressure":
                    return new Color(1f, 0.85f, 0.3f); // Amber / Gold
                default:
                    return new Color(0.9f, 0.95f, 1f); // Off-White
            }
        }
    }
}
