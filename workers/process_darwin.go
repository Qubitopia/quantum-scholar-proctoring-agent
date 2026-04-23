//go:build darwin

package workers

import (
	"os/exec"
	"strings"
)

func getProcessList() string {
	// macOS uses ps instead of tasklist
	cmd := exec.Command("ps", "-A", "-o", "comm=")
	output, _ := cmd.Output()
	return strings.ToLower(string(output))
}

func isCheatingSoftwareRunning() bool {
	processes := getProcessList()

	cheatingSoftware := []string{
		"cheatengine",
		"aimbot",
		"wallhack",
	}

	for _, s := range cheatingSoftware {
		if strings.Contains(processes, s) {
			return true
		}
	}
	return false
}

func isMultipleBrowsersRunning() bool {
	processes := getProcessList()

	browsers := []string{
		"google chrome something something",
	}

	count := 0
	for _, b := range browsers {
		if strings.Contains(processes, strings.ToLower(b)) {
			count++
		}
	}

	return count > 1
}