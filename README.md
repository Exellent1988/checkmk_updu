# RNX UPDU Checkmk Extension

A CheckMK extension for monitoring RNX UPDU (Uninterruptible Power Distribution Unit) devices.

## Development Environment

### Using Development Container (Recommended)

This project includes a pre-configured development container with CheckMK 2.3.0. 

#### Prerequisites
- Docker or Podman
- Visual Studio Code with Dev Containers extension

#### Getting Started
1. Open the project in VS Code
2. When prompted, click "Reopen in Container" or use `Ctrl+Shift+P` → "Dev Containers: Reopen in Container"
3. The container will automatically:
   - Set up CheckMK environment
   - Install required Python dependencies
   - Create symbolic links for the plugin
   - Apply necessary Nagios fixes for compatibility

#### Development Workflow
Once the dev container is running, you need to set up the CheckMK environment:

```bash
# Set password for cmkadmin user
cmk-passwd cmkadmin

# Start CheckMK services
omd start

# Build the extension within the container
.devcontainer/build.sh

# Test the extension
mkp inspect ./build/rnx_updu-0.0.3.mkp
```

The CheckMK web interface is available at `http://localhost:8080/cmk` (user: `cmkadmin`, password: set above).

### Alternative: Manual Docker Setup

If you prefer to run CheckMK manually in Docker:

```bash
REV="${REV:-2.3.0-latest}"

docker run --rm -it -v /tmp/.X11-unix:/tmp/.X11-unix \
    --name checkmk \
    -p 8080:5000 \
    -p 8000:8000 \
    --tmpfs /opt/omd/sites/cmk/tmp:uid=1000,gid=1000 \
    -v /etc/localtime:/etc/localtime:ro \
    --volume=".:/project:rw" \
    checkmk/check-mk-raw:$REV /bin/bash
```

Access CheckMK shell: `omd su cmk`

Then set up the environment:
```bash
# Set password for cmkadmin user
cmk-passwd cmkadmin

# Start CheckMK services
omd start
```

## Build

### Using Development Container
```bash
.devcontainer/build.sh
```

### Manual Build
Run the provided `.devcontainer/build.sh` script to compile the extension:

```bash
./.devcontainer/build.sh
```

The built package will be created in the `build/` directory as `rnx_updu-<version>.mkp`.

## Installation

Install the built plugin in your CheckMK instance:

```bash
mkp add rnx_updu-0.0.3.mkp
mkp enable rnx_updu
```

After installation, you can add and configure RNX UPDU hosts through the CheckMK web interface.

## Testing

### Local Testing with Development Container

1. Follow the development workflow above to set up the environment
2. Build and install the extension:
   ```bash
   .devcontainer/build.sh
   mkp add build/rnx_updu-*.mkp
   mkp enable rnx_updu
   ```
3. Access the CheckMK web interface at `http://localhost:8080/cmk/`
4. Add a new host and configure it to use the RNX UPDU special agent

### Manual Testing

You can also test the plugin components individually:
```bash
# Validate plugin syntax
python3 -m py_compile src/rnx_updu/agent_based/*.py

# Check package contents
mkp inspect ./build/rnx_updu-*.mkp

# List installed packages
mkp list
```

## Troubleshooting

### Common Issues

- **CheckMK services not starting**: Make sure you've run `omd start` after setting up the container
- **Web interface not accessible**: Check that port 5000 is properly forwarded (to 8080 by default) and not blocked by firewall
- **Plugin not loading**: Verify the plugin is properly installed with `mkp list` and enabled with `mkp enable rnx_updu`

### Logs

Check CheckMK logs for debugging:
```bash
# View general CheckMK logs
tail -f ~/var/log/web.log

# View agent output
cmk -v --debug <hostname>

# Check for plugin errors
tail -f ~/var/log/cmc.log
```

## Project Structure

```
├── .devcontainer/          # Development container configuration
│   └── build.sh           # Build script for the extension
├── src/                    # Source code
│   ├── info               # Package metadata
│   └── rnx_updu/          # Plugin package
│       └── agent_based/   # CheckMK agent-based plugins
├── build/                 # Built packages (generated)
├── doc/                   # Documentation
├── VERSION                # Current version
├── RELEASE-NOTES.md       # Release notes and changelog
└── README.md             # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly using the development container
5. Submit a pull request

## License

This project is licensed under the terms specified in the CheckMK licensing.
