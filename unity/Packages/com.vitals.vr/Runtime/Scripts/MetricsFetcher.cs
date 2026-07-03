using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;

namespace VitalsVR
{
    public class MetricsFetcher : MonoBehaviour
    {
        [Header("API Config")]
        [Tooltip("The base URL of the FastAPI server (e.g. http://localhost:8000)")]
        public string apiBaseUrl = "http://localhost:8000";
        
        [Tooltip("Username registered in the Vitals system")]
        public string username = "usuario_prueba";
        
        [Tooltip("Password associated with the username")]
        public string password = "";

        private string accessToken = "";

        public delegate void OnMetricsReceivedDelegate(List<MetricItem> metrics);
        public event OnMetricsReceivedDelegate OnMetricsReceived;

        public delegate void OnStatusMessageDelegate(string message, bool isError);
        public event OnStatusMessageDelegate OnStatusChanged;

        public void FetchMetrics()
        {
            StartCoroutine(FetchMetricsRoutine());
        }

        private IEnumerator FetchMetricsRoutine()
        {
            if (string.IsNullOrEmpty(accessToken))
            {
                yield return StartCoroutine(LoginRoutine());
            }

            if (string.IsNullOrEmpty(accessToken))
            {
                OnStatusChanged?.Invoke("Authentication failed. Cannot fetch metrics.", true);
                yield break;
            }

            OnStatusChanged?.Invoke("Fetching latest metrics...", false);
            string url = $"{apiBaseUrl.TrimEnd('/')}/medidas/ultimas";
            
            using (UnityWebRequest webRequest = UnityWebRequest.Get(url))
            {
                webRequest.SetRequestHeader("Authorization", $"Bearer {accessToken}");
                yield return webRequest.SendWebRequest();

                if (webRequest.result == UnityWebRequest.Result.ConnectionError || 
                    webRequest.result == UnityWebRequest.Result.ProtocolError)
                {
                    if (webRequest.responseCode == 401)
                    {
                        OnStatusChanged?.Invoke("Session expired, re-authenticating...", false);
                        yield return StartCoroutine(LoginRoutine());
                        
                        if (!string.IsNullOrEmpty(accessToken))
                        {
                            yield return StartCoroutine(FetchMetricsRoutine());
                            yield break;
                        }
                    }
                    
                    OnStatusChanged?.Invoke($"Fetch Error: {webRequest.error} (Code {webRequest.responseCode})", true);
                }
                else
                {
                    try
                    {
                        string jsonResult = webRequest.downloadHandler.text;
                        List<MetricItem> metrics = JsonConvert.DeserializeObject<List<MetricItem>>(jsonResult);
                        OnStatusChanged?.Invoke("Metrics updated successfully.", false);
                        OnMetricsReceived?.Invoke(metrics);
                    }
                    catch (Exception ex)
                    {
                        OnStatusChanged?.Invoke($"Failed to parse metrics: {ex.Message}", true);
                    }
                }
            }
        }

        private IEnumerator LoginRoutine()
        {
            OnStatusChanged?.Invoke("Authenticating with Vitals API...", false);
            string url = $"{apiBaseUrl.TrimEnd('/')}/auth/login";

            WWWForm form = new WWWForm();
            form.AddField("username", username);
            form.AddField("password", password);

            using (UnityWebRequest webRequest = UnityWebRequest.Post(url, form))
            {
                yield return webRequest.SendWebRequest();

                if (webRequest.result == UnityWebRequest.Result.ConnectionError || 
                    webRequest.result == UnityWebRequest.Result.ProtocolError)
                {
                    OnStatusChanged?.Invoke($"Login failed: {webRequest.error} (Code {webRequest.responseCode})", true);
                    accessToken = "";
                }
                else
                {
                    try
                    {
                        string jsonResult = webRequest.downloadHandler.text;
                        LoginResponse response = JsonConvert.DeserializeObject<LoginResponse>(jsonResult);
                        accessToken = response.access_token;
                        OnStatusChanged?.Invoke("Authenticated.", false);
                    }
                    catch (Exception ex)
                    {
                        OnStatusChanged?.Invoke($"Auth response error: {ex.Message}", true);
                        accessToken = "";
                    }
                }
            }
        }
    }
}
