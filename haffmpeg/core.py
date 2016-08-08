"""Base functionality of ffmpeg HA wrapper."""
import logging
import shlex
import signal
import subprocess

_LOGGER = logging.getLogger(__name__)

ITER_STDOUT = 'OUT'
ITER_STDERR = 'ERR'


class HAFFmpeg(object):
    """Base HA FFmpeg process.

    Object is iterable but only for data streams! For other things use the
    process property to call from Popen object.
    """

    def __init__(self, ffmpeg_bin, chunk_size=1024, iter_input=ITER_STDOUT):
        """Base initialize."""
        self._ffmpeg = ffmpeg_bin
        self._argv = [ffmpeg_bin]
        self._chunk_size = chunk_size
        self._iter_input = iter_input
        self._bin_mode = None
        self._proc = None

    # pylint: disable=too-many-arguments
    def open(self, cmd, output="-", extra_cmd=None, text=False,
             stdout_pipe=True, stderr_pipe=False):
        """Start a ffmpeg instance and pipe output."""
        stdout = subprocess.PIPE if stdout_pipe else subprocess.DEVNULL
        stderr = subprocess.PIPE if stderr_pipe else subprocess.DEVNULL

        if self._proc is not None:
            _LOGGER.critical("FFmpeg is allready running!")
            return

        # add cmds
        self._argv.extend(cmd)

        # exists a extra cmd from customer
        if extra_cmd is not None:
            self._argv.extend(shlex.split(extra_cmd))

        # add output
        self._argv.append(output)

        # start ffmpeg
        _LOGGER.debug("Start FFmpeg with %s.", str(self._argv))
        self._proc = subprocess.Popen(
            self._argv,
            stderr=stderr,
            stdout=stdout,
            stdin=subprocess.PIPE,
            universal_newlines=text
        )

        # save bin/text mode of process
        self._bin_mode = False if text else True

    def close(self, timeout=5):
        """Stop a ffmpeg instance."""
        if self._proc is None or self._proc.poll() is not None:
            _LOGGER.error("FFmpeg isn't running!")
            return

        # set stop command for ffmpeg
        stop = b'q' if self._bin_mode else 'q'

        try:
            # send stop to ffmpeg
            self._proc.communicate(input=stop, timeout=timeout)
            _LOGGER.debug("Close FFmpeg process.")
        except subprocess.TimeoutExpired:
            _LOGGER.warning("Timeout while waiting of FFmpeg.")
            self._proc.kill()
            self._proc.wait()

        # clean ffmpeg cmd
        self._argv = [self._ffmpeg]
        self._proc = None
        self._bin_mode = None

    @property
    def process(self):
        """Return a Popen object or None of not running."""
        return self._proc

    def __iter__(self):
        """Read data from ffmpeg PIPE/STDERR as iter."""
        return self

    def __next__(self):
        """Get next buffer data."""
        if self._proc is None or self._proc.poll() is not None:
            _LOGGER.debug("don't exists data from a process.")
            raise StopIteration

        # generate reading from
        if self._iter_input == ITER_STDERR:
            read_from = self._proc.stderr
        else:
            read_from = self._proc.stdout

        # check if reading from pipe
        if read_from is None:
            _LOGGER.critical("Iterator havn't data to  read from!")
            raise StopIteration

        return read_from.read(self._chunk_size)
