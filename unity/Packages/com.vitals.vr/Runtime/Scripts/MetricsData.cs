using System;

namespace VitalsVR
{
    [Serializable]
    public class MetricItem
    {
        public string provider;
        public string device;
        public string metric;
        public string unit;
        public float value;
        public string measurement_date;
        public string registration_date;
    }

    [Serializable]
    public class LoginResponse
    {
        public string access_token;
        public string token_type;
    }
}
