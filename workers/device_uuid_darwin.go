 //go:build darwin

package workers

import (
	"fmt"
	"os/exec"
	"regexp"
	"strings"
)

var macUUIDRegex = regexp.MustCompile(`"IOPlatformUUID" = "([^"]+)"`)

func getDeviceUUID() (string, error) {
	cmd := exec.Command("ioreg", "-rd1", "-c", "IOPlatformExpertDevice")
	output, err := cmd.Output()
	if err != nil {
		return "", err
	}

	matches := macUUIDRegex.FindStringSubmatch(string(output))
	if len(matches) > 1 {
		return strings.TrimSpace(matches[1]), nil
	}

	return "", fmt.Errorf("device UUID not found")
}