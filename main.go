package main

import (
	"bytes"
	"fmt"
	"log"
	"math/rand"
	"net"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"time"

	"github.com/google/gopacket"
	"github.com/google/gopacket/layers"
	"github.com/google/gopacket/pcap"
)

func main() {
	// Set up logging to a file
	logFile, err := os.OpenFile("autoauth.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatalf("Failed to open log file: %v", err)
	}
	defer logFile.Close()
	log.SetOutput(logFile)

	log.Println("Starting auto-authentication program")

	// Detect the network interface automatically
	iface, err := detectInterface()
	if err != nil {
		log.Fatalf("Error detecting network interface: %v", err)
		return
	}
	log.Printf("Using network interface: %s\n", iface)

	// Generate a random number for the autoauth command
	rand.Seed(time.Now().UnixNano())
	randomNumber := rand.Intn(1000000)

	// Scan the network to find connected devices
	devices, err := getDevicesOnNetwork(iface)
	if err != nil {
		log.Fatalf("Error getting devices: %v", err)
		return
	}

	log.Printf("Found %d devices on the network\n", len(devices))

	// Try to connect to each device and send the autoauth command
	for _, ip := range devices {
		err := sendAutoAuth(ip, randomNumber)
		if err != nil {
			log.Printf("Error connecting to %s: %v\n", ip, err)
		}
	}
}

// detectInterface automatically detects the network interface based on the OS
func detectInterface() (string, error) {
	var iface string

	switch runtime.GOOS {
	case "linux":
		iface = "eth0"
	case "darwin":
		out, err := exec.Command("sh", "-c", "route get default | grep 'interface:' | awk '{print $2}'").Output()
		if err != nil {
			return "", fmt.Errorf("could not detect interface on macOS: %v", err)
		}
		iface = strings.TrimSpace(string(out))
	case "windows":
		out, err := exec.Command("ipconfig", "/all").Output()
		if err != nil {
			return "", fmt.Errorf("could not detect interface on Windows: %v", err)
		}
		iface = parseWindowsInterface(string(out))
	default:
		return "", fmt.Errorf("unsupported OS: %s", runtime.GOOS)
	}

	if iface == "" {
		return "", fmt.Errorf("could not detect network interface")
	}
	return iface, nil
}

// parseWindowsInterface parses the output of ipconfig to find the active interface
func parseWindowsInterface(output string) string {
	lines := strings.Split(output, "\n")
	for _, line := range lines {
		if strings.Contains(line, "IPv4 Address") {
			return strings.TrimSpace(strings.Split(line, ":")[0])
		}
	}
	return ""
}

// getDevicesOnNetwork scans the network for devices connected to the specified interface
func getDevicesOnNetwork(iface string) ([]string, error) {
	var devices []string
	seenIPs := make(map[string]bool)

	// Open the interface for packet capture
	handle, err := pcap.OpenLive(iface, 1600, true, pcap.BlockForever)
	if err != nil {
		return nil, fmt.Errorf("error opening interface: %v", err)
	}
	defer handle.Close()

	// Set the filter to capture only ARP packets
	if err := handle.SetBPFFilter("arp"); err != nil {
		return nil, fmt.Errorf("error setting filter: %v", err)
	}

	log.Println("Listening for ARP packets to detect devices on the network...")

	// Capture ARP packets to find devices
	packetSource := gopacket.NewPacketSource(handle, handle.LinkType())
	for packet := range packetSource.Packets() {
		arpLayer := packet.Layer(layers.LayerTypeARP)
		if arpLayer != nil {
			arpPacket, _ := arpLayer.(*layers.ARP)
			ip := net.IP(arpPacket.SourceProtAddress).String()
			if !seenIPs[ip] {
				devices = append(devices, ip)
				seenIPs[ip] = true
				log.Printf("Detected device with IP: %s\n", ip)
			}
		}
	}

	return devices, nil
}

// sendAutoAuth connects to the given IP on port 5000 and sends the autoauth command
func sendAutoAuth(ip string, randomNumber int) error {
	address := fmt.Sprintf("%s:5000", ip)
	conn, err := net.Dial("tcp", address)
	if err != nil {
		return fmt.Errorf("could not connect to %s: %v", address, err)
	}
	defer conn.Close()

	log.Printf("Connected to %s, sending autoauth command...\n", ip)

	// Send the autoauth command with the random number
	command := fmt.Sprintf("autoauth %d\n", randomNumber)
	_, err = conn.Write([]byte(command))
	if err != nil {
		return fmt.Errorf("could not send command to %s: %v", address, err)
	}

	// Read the response (optional, based on your use case)
	response := make([]byte, 1024)
	n, err := conn.Read(response)
	if err != nil {
		return fmt.Errorf("could not read response from %s: %v", address, err)
	}

	if bytes.Contains(response[:n], []byte(fmt.Sprintf("%d", randomNumber))) {
		log.Printf("Device at %s responded correctly.\n", ip)
	} else {
		log.Printf("Device at %s did not respond correctly.\n", ip)
	}

	return nil
}
