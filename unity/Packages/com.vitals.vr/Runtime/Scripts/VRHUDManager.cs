using UnityEngine;

namespace VitalsVR
{
    public class VRHUDManager : MonoBehaviour
    {
        [Header("API Reference")]
        public MetricsFetcher fetcher;

        [Header("UI Panel Groups")]
        [Tooltip("The central login panel to enter credentials.")]
        public GameObject loginPanel;

        [Tooltip("The side HUD displaying live patient metrics.")]
        public GameObject metricsHUDPanel;

        [Tooltip("The bottom-right toggle button to open connection settings.")]
        public GameObject loginToggleButton;

        private void Start()
        {
            if (fetcher == null)
                fetcher = GetComponent<MetricsFetcher>();

            if (fetcher != null)
            {
                fetcher.OnMetricsReceived += HandleMetricsReceived;
                fetcher.OnStatusChanged += HandleStatusChanged;
            }

            // Initial state: Hide panels, show only the settings toggle button
            if (loginPanel != null) loginPanel.SetActive(false);
            if (metricsHUDPanel != null) metricsHUDPanel.SetActive(false);
            if (loginToggleButton != null) loginToggleButton.SetActive(true);
        }

        private void OnDestroy()
        {
            if (fetcher != null)
            {
                fetcher.OnMetricsReceived -= HandleMetricsReceived;
                fetcher.OnStatusChanged -= HandleStatusChanged;
            }
        }

        /// <summary>
        /// Public toggle action wired to the login toggle button click.
        /// </summary>
        public void ToggleLoginPanel()
        {
            if (loginPanel != null)
            {
                bool nextState = !loginPanel.activeSelf;
                loginPanel.SetActive(nextState);

                // If we are opening the credentials panel, temporarily hide the metrics HUD
                if (nextState && metricsHUDPanel != null)
                {
                    metricsHUDPanel.SetActive(false);
                }
            }
        }

        private void HandleMetricsReceived(System.Collections.Generic.List<MetricItem> metrics)
        {
            // Successfully fetched metrics: close connection window, open live AR metrics HUD
            if (loginPanel != null) loginPanel.SetActive(false);
            if (metricsHUDPanel != null) metricsHUDPanel.SetActive(true);
        }

        private void HandleStatusChanged(string message, bool isError)
        {
            // If connection errors occur, keep the login window open for editing credentials
            if (isError && loginPanel != null)
            {
                loginPanel.SetActive(true);
            }
        }
    }
}
