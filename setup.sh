#!/bin/bash

# Function to get the latest Go version
get_latest_go_version() {
    curl -s https://go.dev/dl/ | grep -oP 'go[0-9]+\.[0-9]+(\.[0-9]+)?\.linux-arm64\.tar\.gz' | head -1
}

# Function to check if Go is installed and if it matches the latest version
check_existing_go() {
    if command -v go > /dev/null 2>&1; then
        local installed_version
        installed_version=$(go version | grep -oP 'go[0-9]+\.[0-9]+(\.[0-9]+)?')
        local latest_version
        latest_version=$(get_latest_go_version | grep -oP 'go[0-9]+\.[0-9]+(\.[0-9]+)?')

        if [[ $installed_version == $latest_version ]]; then
            echo "Go is already installed and up-to-date (version $installed_version)."
            return 0
        else
            echo "A different version of Go is installed ($installed_version). Skipping installation."
            return 1
        fi
    else
        return 2
    fi
}

# Download and install the latest Go version
install_golang() {
    local go_version
    go_version=$(get_latest_go_version)
    
    echo "Downloading Go $go_version..."
    wget https://golang.org/dl/$go_version -O /tmp/go.tar.gz
    
    echo "Extracting Go $go_version..."
    sudo rm -rf /usr/local/go
    sudo tar -C /usr/local -xzf /tmp/go.tar.gz

    # Set up Go environment variables
    echo "Setting up Go environment variables..."
    if ! grep -q 'export PATH=$PATH:/usr/local/go/bin' ~/.bashrc; then
        echo "export PATH=\$PATH:/usr/local/go/bin" >> ~/.bashrc
    fi

    # Apply the PATH change immediately
    export PATH=$PATH:/usr/local/go/bin

    # Check Go installation
    if command -v go > /dev/null 2>&1; then
        echo "Go has been installed successfully."
    else
        echo "Failed to install Go."
        exit 1
    fi
}

# Set up ENC28J60 as an Ethernet adapter with DHCP
setup_enc28j60() {
    echo "Setting up ENC28J60 Ethernet adapter..."

    # Load ENC28J60 module
    sudo modprobe enc28j60

    # Create network interface configuration
    echo "Creating network interface configuration..."
    cat <<EOF | sudo tee /etc/systemd/network/10-enc28j60.network > /dev/null
[Match]
Name=eth0

[Network]
Address=192.168.50.1/24
DHCPServer=yes
EOF

    # Set up DHCP server for local network
    echo "Setting up DHCP server..."
    sudo systemctl restart systemd-networkd

    # Configure firewall to prevent internet access but allow local network communication
    echo "Configuring firewall to block internet access..."
    sudo iptables -A FORWARD -i eth0 -o wlan0 -j DROP
    sudo iptables -A FORWARD -i wlan0 -o eth0 -m state --state ESTABLISHED,RELATED -j ACCEPT
    sudo iptables -A FORWARD -i eth0 -o eth0 -j ACCEPT
    sudo iptables -A INPUT -i eth0 -j ACCEPT
    sudo iptables -A OUTPUT -o eth0 -j ACCEPT

    echo "ENC28J60 Ethernet adapter has been set up successfully."
}

# Function to test Ethernet connection
test_ethernet() {
    echo "Testing Ethernet connection..."

    # Bring up the Ethernet interface
    sudo ip link set eth0 up

    # Test if the interface is up and has a carrier
    ip link show eth0 | grep -q "state UP"
    if [ $? -eq 0 ]; then
        echo "Ethernet interface is up."
        
        # Try pinging the router or another known local IP
        ping -c 4 192.168.50.1 > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "Ethernet connection is working. Ping successful."
        else
            echo "Ethernet connection is up, but ping failed. Please check your network configuration."
        fi
    else
        echo "Ethernet interface is not up. Please check your hardware or configuration."
    fi
}

# Main execution
if check_existing_go; then
    echo "Skipping Go installation."
else
    install_golang
fi
setup_enc28j60
test_ethernet

echo "Installing libgpiod-dev"
sudo apt-get install -y gpiod libgpiod-dev


echo "All tasks completed successfully."
