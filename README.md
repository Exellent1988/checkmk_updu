# RNX UPDU Checkmk Extension

## Build

Run the provided `build.sh` script to compile the extension.

## Test

CheckMK may be run in a docker container:

```bash
REV="${REV:-2.4.0-2024.09.24}"

docker run --rm -it -v /tmp/.X11-unix:/tmp/.X11-unix \
    --name checkmk \
    -p 8080:5000 \
    -p 8000:8000 \
    --tmpfs /opt/omd/sites/cmk/tmp:uid=1000,gid=1000 \
    -v /etc/localtime:/etc/localtime:ro \
    --volume=".:/project:rw" \
    checkmk/check-mk-raw:$REV /bin/bash
```

The server may be started using the command `omd start cmk`

The checkmk shell may be accessed inside the docker container 
using the command `omd su cmk`.

Then the built plugin may be activated using following commands: 

```Bash
mkp add /project/build/rnx_updu-0.0.2.mkp
mkp enable rnx_updu
```

At this point, hosts may be added in the frontend.
The frontend may be accessed from the host
using`http://[ip of container]:5000/cmk`.
