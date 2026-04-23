package main

import (
	"log"
	"net/http"

	"github.com/Qubitopia/quantum-scholar-proctoring-agent/handlers"
	"github.com/Qubitopia/quantum-scholar-proctoring-agent/workers"
)

func main() {
	// Get device UUID
	deviceUUID, err := workers.GetDeviceUUID()
	if err != nil {
		log.Println("Error getting device UUID:", err)
		return
	}

	handlers.SetDeviceUUID(deviceUUID)
	log.Printf("Device UUID: %s\n", deviceUUID)

	// Start worker in background
	go workers.Monitor(handlers.UpdateStatus)

	// Routes
	http.HandleFunc("/jwt", handlers.WithCORS(handlers.JWTHandler))
	http.HandleFunc("/health", handlers.WithCORS(handlers.HealthHandler))
	http.HandleFunc("/end", handlers.WithCORS(handlers.CloseSoftware))

	log.Println("Server running on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
