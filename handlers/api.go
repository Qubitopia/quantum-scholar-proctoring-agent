package handlers

import (
	"encoding/json"
	"net/http"
	"os"
	"sync"
)

var allowedOrigins = map[string]struct{}{
	"http://localhost:3000":       {},
	"https://quantumscholar.pages.dev": {},
}

var (
	statusMutex sync.RWMutex
	status      string
	globalJWT   string
	deviceUUID  string
)

func SetDeviceUUID(uuid string) {
	deviceUUID = uuid
}

func WithCORS(handler http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		if _, ok := allowedOrigins[origin]; ok {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Vary", "Origin")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		}

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}

		handler(w, r)
	}
}

// Response struct
type HealthResponse struct {
	Status string `json:"status"`
	UUID   string `json:"uuid"`
	JWT    string `json:"jwt,omitempty"`
}

// Store JWT
func JWTHandler(w http.ResponseWriter, r *http.Request) {
	jwt := r.URL.Query().Get("token")
	if jwt == "" {
		http.Error(w, "Missing token", http.StatusBadRequest)
		return
	}

	globalJWT = jwt

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"message": "JWT stored successfully",
	})
}

// Health endpoint
func HealthHandler(w http.ResponseWriter, r *http.Request) {
	statusMutex.RLock()
	currentStatus := status
	statusMutex.RUnlock()

	response := HealthResponse{
		Status: currentStatus,
		UUID:   deviceUUID,
		JWT:    globalJWT,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// Update status safely
func UpdateStatus(newStatus string) {
	statusMutex.Lock()
	defer statusMutex.Unlock()
	status = newStatus
}


func CloseSoftware(w http.ResponseWriter, r *http.Request) {
	// Implement logic to close the software gracefully
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"message": "Software closing initiated",
	})
	// You can add logic here to signal the worker to stop or perform cleanup
	os.Exit(0)
}