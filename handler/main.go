package handler

import (
	"fmt"

	"github.com/warthog618/go-gpiocdev"
)

type GPIOHandler struct {
	pulseCount   int
	lastStateA   bool
	lastStateB   bool
	buttonEvents map[int]func(bool) // Map to store button event handlers
	scrollEvent  func(int)          // Function to handle scroll events
	lines        []*gpiocdev.Line   // Store lines to keep them open
}

// NewHandler initializes the GPIO handler
func NewHandler() *GPIOHandler {
	return &GPIOHandler{
		buttonEvents: make(map[int]func(bool)),
		lines:        make([]*gpiocdev.Line, 0), // Initialize lines slice
	}
}

// AddScrollListener sets the event handler for scroll events
func (gh *GPIOHandler) AddScrollListener(handler func(int)) {
	gh.scrollEvent = handler
}

// AddButtonListener sets the event handler for a specific button
func (gh *GPIOHandler) AddButtonListener(buttonPin int, handler func(bool)) {
	gh.buttonEvents[buttonPin] = handler
}

// InitializeScroll initializes the scroll (quadrature encoder)
func (gh *GPIOHandler) InitializeScroll(pinA, pinB int) error {
	lineA, err := gpiocdev.RequestLine("gpiochip0", pinA, gpiocdev.AsInput, gpiocdev.WithPullUp, gpiocdev.WithBothEdges, gpiocdev.WithEventHandler(gh.scrollEventHandler))
	if err != nil {
		return fmt.Errorf("error requesting line %d: %v", pinA, err)
	}
	gh.lines = append(gh.lines, lineA) // Keep the line open

	lineB, err := gpiocdev.RequestLine("gpiochip0", pinB, gpiocdev.AsInput, gpiocdev.WithPullUp, gpiocdev.WithBothEdges, gpiocdev.WithEventHandler(gh.scrollEventHandler))
	if err != nil {
		return fmt.Errorf("error requesting line %d: %v", pinB, err)
	}
	gh.lines = append(gh.lines, lineB) // Keep the line open

	return nil
}

// InitializeButton initializes a button
func (gh *GPIOHandler) InitializeButton(buttonPin int) error {
	line, err := gpiocdev.RequestLine("gpiochip0", buttonPin, gpiocdev.AsInput, gpiocdev.WithPullUp, gpiocdev.WithBothEdges, gpiocdev.WithEventHandler(gh.buttonEventHandler))
	if err != nil {
		return fmt.Errorf("error requesting button line %d: %v", buttonPin, err)
	}
	gh.lines = append(gh.lines, line) // Keep the line open

	return nil
}

// scrollEventHandler handles the scroll events
func (gh *GPIOHandler) scrollEventHandler(evt gpiocdev.LineEvent) {
	stateA := gh.lastStateA
	stateB := gh.lastStateB

	if evt.Offset == 263 {
		stateA = (evt.Type == gpiocdev.LineEventRisingEdge)
	} else if evt.Offset == 264 {
		stateB = (evt.Type == gpiocdev.LineEventRisingEdge)
	}

	if stateA != gh.lastStateA {
		if stateA != stateB {
			gh.pulseCount++
		} else {
			gh.pulseCount--
		}
	} else if stateB != gh.lastStateB {
		if stateA == stateB {
			gh.pulseCount++
		} else {
			gh.pulseCount--
		}
	}

	gh.lastStateA = stateA
	gh.lastStateB = stateB

	if gh.scrollEvent != nil {
		gh.scrollEvent(gh.pulseCount)
	}
}

// buttonEventHandler handles button press and release events
func (gh *GPIOHandler) buttonEventHandler(evt gpiocdev.LineEvent) {
	if handler, exists := gh.buttonEvents[evt.Offset]; exists {
		if evt.Type == gpiocdev.LineEventRisingEdge {
			handler(false) // Button released
		} else if evt.Type == gpiocdev.LineEventFallingEdge {
			handler(true) // Button pressed
		}
	}
}
