//go:build windows

package workers

import (
	"os/exec"
	"strings"
)

func getProcessList() string {
	cmd := exec.Command("tasklist")
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
		"chrome.exe",
		"msedge.exe",
		"firefox.exe",
		"brave.exe",
		"opera.exe",
		"vivaldi.exe",
		"iexplore.exe",
		"chromium.exe",
		"tor.exe",
	}

	count := 0
	for _, b := range browsers {
		if strings.Contains(processes, b) {
			count++
		}
	}

	return count > 1
}