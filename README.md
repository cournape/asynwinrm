aio-winrm is licensed under the APACHE 2.0 license.

## About

Python 3.5+ library implementing the WinRM protocol on top of asyncio.

The original repository can be found [here](https://github.com/cournape/aio-winrm)
I've opend a [pull request](https://github.com/cournape/aio-winrm/pull/2) but the original author is probably busy
The sync api might need some love, but I'd recommend using [pyWinRm](https://github.com/diyan/pywinrm) in stead

## New in this fork:
 - SSL support
 - PowerShell support
 - PSRP (PowerShell Remoting Protocol) support


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


## Usage:

```python
import asyncio
from aiohttp import BasicAuth
from aiowinrm import run_cmd, run_ps, run_psrp


async def run_cmd_print(host, auth, cmd, params=()):
    verify_ssl = False  # if using self signed certificate

    res = await run_cmd(host, auth, cmd, params, verify_ssl=verify_ssl)
    std_out, std_err, exit_code = res
    if std_err:
        print('ERROR:\r\n', std_err)


async def run_ps_print(host, auth, script):
    verify_ssl = False  # if using self signed certificate

    res = await run_ps(host, auth, script, verify_ssl=verify_ssl)
    std_out, std_err, exit_code = res
    if std_err:
        print('ERROR:\r\n', std_err)


async def run_psrp_print(host, auth, script):
    verify_ssl = False  # if using self signed certificate

    res = await run_psrp(host, auth, script, verify_ssl=verify_ssl)
    std_out, std_err, exit_code = res
    if std_err:
        print('ERROR:\r\n', std_err)


if __name__ == '__main__':
    host = "https://1.2.3.4"
    auth = BasicAuth("administrator", "password")
    loop = asyncio.get_event_loop()
    coro = run_psrp_print(host, auth, "Get-WmiObject Win32_OperatingSystem")
    # coro = run_cmd_print(host, auth, "netstat -an")

    loop.run_until_complete(coro)
    loop.close()
```