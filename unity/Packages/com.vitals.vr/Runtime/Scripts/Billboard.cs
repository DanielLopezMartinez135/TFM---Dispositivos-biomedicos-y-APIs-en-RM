using UnityEngine;

namespace VitalsVR
{
    public class Billboard : MonoBehaviour
    {
        [Tooltip("The camera transform the panel should face. Defaults to Camera.main if left blank.")]
        public Transform targetCamera;

        [Tooltip("If true, the panel will only rotate around the Y axis (vertical), keeping it upright.")]
        public bool useXZOnly = true;

        private void Start()
        {
            if (targetCamera == null && Camera.main != null)
            {
                targetCamera = Camera.main.transform;
            }
        }

        private void LateUpdate()
        {
            if (targetCamera == null && Camera.main != null)
            {
                targetCamera = Camera.main.transform;
            }

            if (targetCamera == null) return;

            Vector3 targetPosition = targetCamera.position;
            
            if (useXZOnly)
            {
                targetPosition.y = transform.position.y;
            }

            transform.LookAt(targetPosition);
            transform.Rotate(0, 180, 0);
        }
    }
}
