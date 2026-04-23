 //go:build windows

package workers

import (
	"fmt"
	"strings"

	"github.com/StackExchange/wmi"
)

func getDeviceUUID() (string, error) {
	type Win32_ComputerSystemProduct struct {
		UUID string
	}

	var dst []Win32_ComputerSystemProduct
	query := "SELECT UUID FROM Win32_ComputerSystemProduct"

	err := wmi.Query(query, &dst)
	if err != nil {
		return "", err
	}

	if len(dst) > 0 &&
		dst[0].UUID != "" &&
		dst[0].UUID != "00000000-0000-0000-0000-000000000000" {
		return strings.TrimSpace(dst[0].UUID), nil
	}

	return "", fmt.Errorf("device UUID not found")
}