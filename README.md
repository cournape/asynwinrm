aio-winrm is licensed under the APACHE 2.0 license.

## About

Python 3.5+ library implementing the WinRM protocol on top of asyncio.

The original repository can be found [here](https://github.com/cournape/aio-winrm).
I've opend a [pull request](https://github.com/cournape/aio-winrm/pull/2) but the original author is probably busy.
The sync api might need some love, but I'd recommend using [pyWinRm](https://github.com/diyan/pywinrm) in stead.


## Features

 - PowerShell support
 - PSRP (PowerShell Remoting Protocol) support (ported from winrb/winrm)
 - SSL support
 - NTLM support (ported from pywinrm)
 - Kerberos support (ported from pywinrm)
 

## What is not (yet?) in this library?

 - CREDSSP (Single Sign On)
 - I havent tested using client certificates yet it probably doesn't work yet but shouldn't be hard to implement


## Why this fork?:

PSRP support. After a few tests I hit the same 8k characater limit that [this](http://www.hurryupandwait.io/about/) Ruby Dev came across.
His blog post on PSRP is a good read: [A look under the hood at Powershell Remoting through a cross plaform lens](http://www.hurryupandwait.io/blog/a-look-under-the-hood-at-powershell-remoting-through-a-ruby-cross-plaform-lens)

Why not [pyWinRm](https://github.com/diyan/pywinrm):

- I needed something async to do lots of requests at the same time.

Why not [txwinrm](https://github.com/zenoss/txwinrm):

- Our project is moving away from twisted and towards asyncio where possible.


## PSRP

I've shamelessly ported most of the PSRP code in [Ruby WinRm](https://github.com/WinRb/WinRM)
You'll notice that the PSRP code mostly reflects the structure in the WinRb/WinRm library


## Some security guidelines

I am not a security expert. I've only ported the code from the respective libraries.
I do have the following suggestions for users though:

 - Please don't use plain text. I've added an extra check to prevent you from unintentionaly doing so
 - Please don't use NTLM without SSL we use message encryption but it uses RC4 and MD5
 - Prefer using Kerberos so that you don't send your credentials to a possibly compromised host

## Usage:

```python
import asyncio
from aiowinrm import \
    run_cmd, \
    run_ps, \
    run_psrp, \
    build_win_rm_url, \
    ConnectionOptions, \
    AuthEnum


def print_output(res):
    std_out, std_err, exit_code = res
    if std_out:
        print('OUTPUT:\r\n', std_out)
    if std_err:
        print('ERROR:\r\n', std_err)


async def run_cmd_print(conn_opts, cmd, params=()):
    res = await run_cmd(conn_opts, cmd, params)
    print_output(res)


async def run_ps_print(conn_opts, script):
    res = await run_ps(conn_opts, script)
    print_output(res)


async def run_psrp_print(conn_opts, script):
    res = await run_psrp(conn_opts, script)
    print_output(res)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    connection_options = ConnectionOptions(
        winrm_url=build_win_rm_url('1.2.3.4', use_https=True),
        auth_method=AuthEnum.Basic,  # since we're using https anyway
        username='administrator',
        password='password',
        verify_ssl=False,  # if using self signed certificate
        loop=loop
    )
    coro = run_psrp_print(connection_options, "Get-WmiObject Win32_OperatingSystem")
    #coro = run_cmd_print(connection_options, "netstat -an")

    loop.run_until_complete(coro)
    loop.close()
```

## Kerberos:

When developing the Kerberos implementation I had some initial trouble setting up this on my mac.
I resolved to writing a Dockerfile which also nicely documents some requirements on an OS level.

```
docker build . -t aiowinrm
```

Note that Kerberos requires a DNS. In my case I was running an AD server in my VM.
On my development machine I had to add some the following line to make it work:

```
1.2.3.4 hostname domain-name.local hostname.domain-name.local
```

The usages are as follows:

 - `hostname` for when I just run a winrm call to the specified host without the `domain-name`
 - `domain-name.local` which is usually the address of your active directoy. This is used to retrieve the kerberos ticket
 - `hostname.domain-name.local` in case you want either or both of the above addresses to be FQDNs


## Some timings

Note that [YMMV](https://www.urbandictionary.com/define.php?term=ymmv)


All timings are requests from a local docker instance to a local vm.
Every request will open a new shell for the request and close it afterwards
In case of kerberos I kept the timings outside since you can keep using the same token.
WHen using Kerberos or NTLM over HTTP we use message encryption

```
Basic + HTTP:     0.32 - 0.36 sec
Basic + HTTPS:    0.33 - 0.36 sec
NTLM + HTTP:      0.41 - 0.45 sec
NTLM + HTTPS:     0.36 - 0.42 sec
Kerberos + HTTP:  0.30 - 0.34 sec
Kerberos + HTTPS: 0.38 - 0.41 sec
```