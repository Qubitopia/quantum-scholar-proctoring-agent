package workers

import (
	"log"
	"time"
)

// Pass status updater function

func Monitor(updateStatus func(string)) {
	for {
		if isCheatingSoftwareRunning() {
			log.Println("Cheating software detected!")
			updateStatus("CHEATING_SOFTWARE_DETECTED")

		} else if isMultipleBrowsersRunning() {
			log.Println("Multiple browsers detected!")
			updateStatus("MULTIPLE_BROWSERS")

		} else {
			updateStatus("OK")
		}

		time.Sleep(5 * time.Second)
	}
}
