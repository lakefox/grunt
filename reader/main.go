package main

import (
	"fmt"
	"time"

	handler "gpio/handler" // replace "yourmodulepath" with the actual module path
)

func main() {
	gh := handler.NewHandler()

	// Set up the scroll event listener
	gh.AddScrollListener(func(count int) {
		fmt.Printf("Scroll event: Pulse count is %d\n", count)
	})

	// Initialize the scroll with the pins for A and B
	if err := gh.InitializeScroll(263, 264); err != nil { // Replace with your actual pin numbers
		fmt.Println("Error initializing scroll:", err)
		return
	}

	// Set up button event listeners
	gh.AddButtonListener(265, func(pressed bool) {
		if pressed {
			fmt.Println("Button 1 pressed!")
		} else {
			fmt.Println("Button 1 released!")
		}
	})
	gh.AddButtonListener(266, func(pressed bool) {
		if pressed {
			fmt.Println("Button 2 pressed!")
		} else {
			fmt.Println("Button 2 released!")
		}
	})
	gh.AddButtonListener(267, func(pressed bool) {
		if pressed {
			fmt.Println("Button 3 pressed!")
		} else {
			fmt.Println("Button 3 released!")
		}
	})
	gh.AddButtonListener(268, func(pressed bool) {
		if pressed {
			fmt.Println("Button 4 pressed!")
		} else {
			fmt.Println("Button 4 released!")
		}
	})

	// Initialize buttons
	if err := gh.InitializeButton(265); err != nil {
		fmt.Println("Error initializing button 1:", err)
		return
	}
	if err := gh.InitializeButton(266); err != nil {
		fmt.Println("Error initializing button 2:", err)
		return
	}
	if err := gh.InitializeButton(267); err != nil {
		fmt.Println("Error initializing button 3:", err)
		return
	}
	if err := gh.InitializeButton(268); err != nil {
		fmt.Println("Error initializing button 4:", err)
		return
	}

	// Keep the program running
	for {
		time.Sleep(1 * time.Second)
	}
}
