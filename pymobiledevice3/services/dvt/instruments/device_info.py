import plistlib
import typing
from datetime import datetime

from pymobiledevice3.dtx import DTXNsError, DTXService, dtx_method
from pymobiledevice3.dtx.ns_types import NSDate
from pymobiledevice3.dtx_service import DtxService
from pymobiledevice3.exceptions import DvtDirListError


# This class fully defines the DTX methods, no dynamic lookup is performed.
# If a method is missing, there will be no dynamic lookup and a NSError will be sent to the caller,
# with an invalid selector descritpion.
#
# Method names are automatically converted by @dtx_method to the Objective-C selector form, e.g. directoryListingForPath_ becomes directoryListingForPath: .
# You can also specify the selector explicitly, e.g. @dtx_method("directoryListingForPath:") if the automatic conversion doesn't work for some reason.
# I've included an example of such usage.
#
# @dtx_method also accepts optional arguments to pass to do_invoke, like expect_reply=False for one-way messages.
class _DeviceInfoService(DTXService):
    IDENTIFIER = "com.apple.instruments.server.services.deviceinfo"

    @dtx_method
    async def directoryListingForPath_(self, path: str) -> list[str]: ...

    @dtx_method
    async def execnameForPid_(self, pid: int) -> str: ...

    @dtx_method
    async def runningProcesses(self) -> list[dict]: ...

    @dtx_method("isRunningPid:")  # example of explicitly specifying the selector
    async def is_pid_runnning(self, pid: int) -> bool: ...

    @dtx_method
    async def nameForUID_(self, uid: int) -> str: ...

    @dtx_method
    async def nameForGID_(self, gid: int) -> str: ...

    @dtx_method
    async def systemInformation(self) -> dict: ...

    @dtx_method
    async def hardwareInformation(self) -> dict: ...

    @dtx_method
    async def networkInformation(self) -> dict: ...

    @dtx_method
    async def machTimeInfo(self) -> dict: ...

    @dtx_method
    async def machKernelName(self) -> str: ...

    @dtx_method
    async def kpepDatabase(self) -> bytes | None: ...

    @dtx_method
    async def traceCodesFile(self) -> str: ...


class DeviceInfo(DtxService[_DeviceInfoService]):
    async def ls(self, path: str) -> list:
        """
        List a directory.
        :param path: Directory to list.
        :return: Contents of the directory.
        """
        try:
            result = await (self.service).directoryListingForPath_(path)
        except DTXNsError as e:
            raise DvtDirListError() from e
        if result is None:
            raise DvtDirListError()
        return result

    async def execname_for_pid(self, pid: int) -> str:
        """
        get full path for given pid
        :param pid: process pid
        """
        return await (self.service).execnameForPid_(pid)

    async def proclist(self) -> list[dict]:
        """
        Get the process list from the device.
        :return: List of process and their attributes.
        """
        result = await (self.service).runningProcesses()
        assert isinstance(result, list)
        for process in result:
            if "startDate" in process:
                d = process["startDate"]
                process["startDate"] = d.utc if isinstance(d, NSDate) else datetime.fromtimestamp(d)
        return result

    async def is_running_pid(self, pid: int) -> bool:
        """
        check if pid is running
        :param pid: process identifier
        :return: whether if it is running or not
        """
        return await (self.service).is_pid_runnning(pid)

    async def system_information(self):
        return await self.service.systemInformation()

    async def hardware_information(self):
        return await self.service.hardwareInformation()

    async def network_information(self):
        return await self.service.networkInformation()

    async def mach_time_info(self):
        return await self.service.machTimeInfo()

    async def mach_kernel_name(self) -> str:
        return await self.service.machKernelName()

    async def kpep_database(self) -> typing.Optional[dict]:
        kpep_database = await self.service.kpepDatabase()
        if kpep_database is not None:
            return plistlib.loads(kpep_database)

    async def trace_codes(self):
        codes_file = await self.service.traceCodesFile()
        return {int(k, 16): v for k, v in (line.split() for line in codes_file.splitlines())}

    async def name_for_uid(self, uid: int) -> str:
        return await self.service.nameForUID_(uid)

    async def name_for_gid(self, gid: int) -> str:
        return await self.service.nameForGID_(gid)


# This instead doesn't define the DTX methods and make use of
# the DTXDynamicService fallback to resolve selectors at runtime, which is more flexible but less type-safe and discoverable.
class DynamicDeviceInfo(DtxService):
    def __getattr__(self, name):
        return getattr(self.service, name)
