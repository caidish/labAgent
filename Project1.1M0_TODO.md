# Project 1.1 M0 - Discovery & Control Audit - TODO

## Overview
Establish foundation for Nikon microscope automation by understanding available hardware and control interfaces in the glovebox lab.

**Timeline**: 1-2 days  
**Status**: 🚧 **IN PROGRESS**

---

## Phase 1: Lab Environment Setup
**Responsibility**: User (Lab Setup)

### Tasks
- [ ] **Deploy Development Environment**
  - [ ] Install Python 3.8+ on lab computer
  - [ ] Set up virtual environment for microscope control
  - [ ] Install basic development tools (git, code editor)
  - [ ] Document lab computer specs (OS, CPU, RAM, available ports)

- [ ] **Install Nikon Software/SDK**  
  - [ ] Check if NIS-Elements is already installed
  - [ ] Locate Nikon SDK documentation/installation files
  - [ ] Install vendor-provided drivers for camera
  - [ ] Test NIS-Elements basic functionality (if available)

- [ ] **Basic Connectivity Test**
  - [ ] Verify camera is recognized by system
  - [ ] Test manual image capture through vendor software
  - [ ] Document any error messages or connectivity issues
  - [ ] Note current software versions and configurations

---

## Phase 2: Hardware Discovery & Inventory  
**Responsibility**: Joint (User + Claude)

### Camera Control Investigation
- [ ] **Camera Specifications**
  - [ ] Identify exact Nikon camera model number
  - [ ] Document resolution, sensor type, frame rate capabilities
  - [ ] List available exposure settings (range, increments)
  - [ ] Note gain/ISO controls and available values
  - [ ] Check for additional features (binning, ROI, etc.)

- [ ] **Connection Analysis** 
  - [ ] Determine physical connection type (USB-C, USB3, PCIe, Ethernet)
  - [ ] Identify cable specifications and length constraints
  - [ ] Test connection stability and data transfer rates
  - [ ] Document any connection-related limitations

- [ ] **API Discovery**
  - [ ] Research available control APIs:
    - NIS-Elements SDK (if available)
    - Direct camera drivers/APIs
    - Python libraries (opencv, pylon, etc.)
    - Third-party control software
  - [ ] Test API availability and basic functionality
  - [ ] Document API capabilities and limitations

### Stage Systems Investigation
- [ ] **Stage Controller Identification**
  - [ ] Identify X, Y, Z stage controllers (manufacturer, model)
  - [ ] Document movement ranges for each axis
  - [ ] Note precision specifications (step size, repeatability)
  - [ ] Record maximum speeds and acceleration limits

- [ ] **Control Interface Mapping**
  - [ ] Determine control interfaces (serial, USB, Ethernet, proprietary)
  - [ ] Map serial/USB port assignments for each axis
  - [ ] Identify required drivers or control software
  - [ ] Test basic connectivity to each stage controller

- [ ] **Movement Capabilities**
  - [ ] Document coordinate system and reference points
  - [ ] Test absolute vs relative movement capabilities
  - [ ] Check for soft limits and safety boundaries
  - [ ] Verify position feedback and accuracy

### Illumination & Optics Assessment
- [ ] **Light Source Control**
  - [ ] Identify illumination types (LED, halogen, laser, etc.)
  - [ ] Document intensity control methods and ranges
  - [ ] Note available wavelengths or color channels
  - [ ] Test on/off control and intensity adjustment

- [ ] **Optical Components**
  - [ ] Map available objectives (magnifications, working distances)
  - [ ] Document filter wheels and available filters
  - [ ] Note aperture controls and focusing mechanisms
  - [ ] Identify automated vs manual components

### Safety & Interlocks Survey
- [ ] **Glovebox Integration**
  - [ ] Identify glovebox door sensors and interlocks
  - [ ] Document pressure monitoring systems
  - [ ] Check for atmosphere control integration
  - [ ] Note any environmental sensors (humidity, temperature)

- [ ] **Emergency Systems**
  - [ ] Locate emergency stop buttons and controls
  - [ ] Document Z-axis collision protection systems
  - [ ] Check for software-based safety limits
  - [ ] Test emergency stop functionality

---

## Phase 3: Control Interface Mapping
**Responsibility**: Joint (User + Claude)

### Transport Layer Analysis
- [ ] **Communication Protocols**
  - [ ] Map all USB/Serial port assignments
  - [ ] Document baud rates and communication parameters
  - [ ] Test network interfaces (if applicable)
  - [ ] Note any proprietary communication protocols

- [ ] **Driver Requirements**
  - [ ] List all required device drivers
  - [ ] Verify driver installation and compatibility
  - [ ] Document driver versions and update procedures
  - [ ] Note any permission/administrative requirements

### Software Stack Evaluation
- [ ] **Vendor Software Integration**
  - [ ] Assess NIS-Elements automation capabilities
  - [ ] Document available scripting interfaces
  - [ ] Test macro recording and playback features
  - [ ] Evaluate export/import capabilities

- [ ] **Direct Programming Interfaces**
  - [ ] Test Python library availability and functionality
  - [ ] Document C/C++ SDK capabilities (if available)
  - [ ] Evaluate COM/ActiveX interfaces (Windows)
  - [ ] Test command-line tools and utilities

### Command Discovery & Documentation
- [ ] **Camera Commands**
  - [ ] Document image capture commands and parameters
  - [ ] List exposure and gain control methods
  - [ ] Note image format options (TIFF, JPG, RAW, etc.)
  - [ ] Test live preview and streaming capabilities

- [ ] **Stage Commands**
  - [ ] Document movement commands (absolute, relative)
  - [ ] List homing and calibration procedures
  - [ ] Note position query and feedback methods
  - [ ] Test speed and acceleration control

- [ ] **System Commands**
  - [ ] Document initialization and shutdown procedures
  - [ ] List status query and error reporting methods
  - [ ] Note logging and diagnostic capabilities
  - [ ] Test configuration save/load functionality

---

## Phase 4: Proof of Concept Testing
**Responsibility**: Claude (with user assistance for hardware testing)

### Basic Camera Script Development
- [ ] **Minimal Camera Control**
  - [ ] Write script to initialize camera connection
  - [ ] Implement basic exposure and gain setting
  - [ ] Create image capture and save functionality
  - [ ] Add error handling and cleanup procedures

- [ ] **Testing & Validation**
  - [ ] Test script on actual hardware
  - [ ] Verify image quality and consistency
  - [ ] Validate parameter ranges and limits
  - [ ] Document any issues or limitations

### Stage Movement Script Development  
- [ ] **Basic Stage Control**
  - [ ] Write script to initialize stage controllers
  - [ ] Implement absolute and relative movement functions
  - [ ] Create position query and feedback methods
  - [ ] Add safety checks and error handling

- [ ] **Testing & Validation**
  - [ ] Test movement accuracy and repeatability
  - [ ] Verify safety limits and collision protection
  - [ ] Validate position feedback consistency
  - [ ] Document movement performance metrics

### Integration Testing
- [ ] **Combined Operation Sequence**
  - [ ] Create script for: Home → Move → Focus → Snap
  - [ ] Test sequence repeatability (minimum 3 runs)
  - [ ] Measure timing and performance metrics
  - [ ] Validate data consistency and quality

- [ ] **Error Handling & Recovery**
  - [ ] Test error conditions and recovery procedures
  - [ ] Validate safety system integration
  - [ ] Document failure modes and solutions
  - [ ] Create troubleshooting procedures

---

## Deliverables

### 1. Hardware Inventory Document (`docs/hardware_inventory.md`)
**Content Requirements:**
- [ ] Complete device list with model numbers and specifications
- [ ] Physical connection diagrams and port assignments  
- [ ] Control interface summary table
- [ ] Performance specifications and limitations
- [ ] Vendor contact information and support resources

### 2. Command Reference (`docs/command_reference.md`)
**Content Requirements:**
- [ ] Complete API reference for all devices
- [ ] Parameter ranges and valid values
- [ ] Error codes and troubleshooting guide
- [ ] Example commands and usage patterns
- [ ] Performance benchmarks and timing data

### 3. Test Scripts (`scripts/proof_of_concept/`)
**Required Scripts:**
- [ ] `camera_test.py` - Basic camera control and capture
- [ ] `stage_test.py` - Stage movement and positioning
- [ ] `integration_test.py` - Combined operation sequence
- [ ] `safety_test.py` - Emergency stop and safety validation
- [ ] `performance_test.py` - Timing and accuracy measurements

### 4. Technical Specification (`docs/M0_technical_spec.md`)
**Content Requirements:**
- [ ] System architecture overview and recommendations
- [ ] MCP server design specifications for M1
- [ ] Safety requirements and implementation guidelines
- [ ] Performance requirements and acceptance criteria
- [ ] Risk assessment and mitigation strategies

---

## Acceptance Criteria

### Functional Requirements
- ✅ **Stage Control**: Can move stage to specific X,Y,Z coordinates from script with ±5μm accuracy
- ✅ **Image Capture**: Can capture images with programmatic exposure control (range: 1ms-10s)
- ✅ **Repeatability**: All operations succeed 3/3 times with consistent results
- ✅ **Safety**: Emergency stops function correctly and prevent hardware damage

### Documentation Requirements
- ✅ **Completeness**: All hardware components identified and documented
- ✅ **Accuracy**: Technical specifications verified through testing
- ✅ **Usability**: Documentation enables M1 implementation planning

### Code Quality
- ✅ **Functionality**: Test scripts run without errors on target hardware
- ✅ **Robustness**: Error handling prevents system crashes or damage
- ✅ **Maintainability**: Code is documented and follows Python best practices

---

## Success Metrics

**Time to Complete**: ≤ 2 days  
**Hardware Coverage**: 100% of available components documented  
**API Coverage**: ≥ 90% of required functions identified and tested  
**Test Success Rate**: 100% for basic operations, ≥ 95% for complex sequences  
**Documentation Quality**: Technical review approval for M1 planning

---

## Risk Assessment & Mitigation

### High Risk Items
- **Hardware Damage**: Implement safety checks and limits in all scripts
- **Driver Compatibility**: Test on actual lab computer environment early
- **API Availability**: Have backup plans for direct hardware control
- **Access Permissions**: Coordinate with lab admin for required privileges

### Mitigation Strategies
- Start with read-only operations (queries, status checks)
- Test with minimal movement ranges before full capability testing
- Maintain backup/rollback procedures for all software changes
- Document all changes for easy system restoration

---

**Next Phase**: Upon completion, proceed to **Project 1.1 M1** - MCP Skeleton & Tool Contracts