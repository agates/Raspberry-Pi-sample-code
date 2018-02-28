#!/usr/bin/env python3

##############################################################################
#
# Originally written by Atlas Scientific
#
# Updated to Python 3.x by Dominic Bolding for The Raspberry Pi - 2016
# Updated by Alecks Gates
#
# Contact: admin@myhydropi.com, agates@mail.agates.io
#
##############################################################################

import fcntl  # used to access I2C parameters like addresses
import io  # used to create file streams
import time  # used for sleep delay and timestamps


class AtlasI2c:
    # the timeout needed to query readings and
    # calibrations
    long_timeout = 1.5

    # timeout for regular commands
    short_timeout = .5

    # the default bus for I2C on the newer Raspberry Pis,
    # certain older boards use bus 0
    default_bus = 1

    # the default address for the pH sensor
    default_address = 99

    def __init__(self, address=default_address, bus=default_bus):
        self.current_addr = address
        # open two file streams, one for reading and one for writing
        # the specific I2C channel is selected with bus
        # it is usually 1, except for older revisions where its 0
        # wb and rb indicate binary read and write
        self.file_read = io.open("/dev/i2c-" + str(bus), "r+b", buffering=0)
        self.file_write = io.open("/dev/i2c-" + str(bus), "wb", buffering=0)

        # initializes I2C to either a user specified or default address
        self.set_i2c_address(address)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.file_read.close()
        self.file_write.close()

    def set_i2c_address(self, addr):
        # set the I2C communications to the slave specified by the address
        # The commands for I2C dev using the ioctl functions are specified in
        # the i2c-dev.h file from i2c-tools
        I2C_SLAVE = 0x703
        fcntl.ioctl(self.file_read, I2C_SLAVE, addr)
        fcntl.ioctl(self.file_write, I2C_SLAVE, addr)
        self.current_addr = addr

    def write(self, string):
        # appends the null character and sends the string over I2C
        self.file_write.write("{}\00".format(string).encode('UTF-8'))

    def read_bytes(self, num_of_bytes=31):
        # reads a specified number of bytes from I2C,
        # then parses and displays the result

        # read from the board
        res = self.file_read.read(num_of_bytes)

        # remove the null characters to get the response
        response = (x for x in res if x != 0)
        reponse_code = next(response)
        if reponse_code == 1:
            # if the response isnt an error
            # change MSB to 0 for all received characters
            # NOTE: having to change the MSB to 0 is a glitch in the
            # raspberry pi, and you shouldn't have to do this!
            # convert the char list to a bytes
            return bytes(x & ~0x80 for x in response)
        else:
            raise Exception("Error {}".format(reponse_code))

    def read(self, num_of_bytes=31):
        return self.read_bytes(num_of_bytes).decode('UTF-8')

    def query_bytes(self, string):
        # write a command to the board, wait the correct timeout,
        # and read the response
        self.write(string)

        string_upper = string.upper()

        # the read and calibration commands require a longer timeout
        if string_upper.startswith("R") \
                or string_upper.startswith("CAL"):
            time.sleep(self.long_timeout)
        elif string_upper.startswith("SLEEP"):
            raise Exception("sleep mode")
        else:
            time.sleep(self.short_timeout)
        return self.read_bytes()

    def query(self, string):
        return self.query_bytes(string).decode("UTF-8")

    def list_i2c_devices(self):
        # save the current address so we can restore it after
        orig_addr = self.current_addr

        i2c_devices = []
        for i in range(0, 128):
            try:
                self.set_i2c_address(i)
                self.read_bytes()
                i2c_devices.append(i)
            except IOError:
                pass

        # restore the address we were using
        self.set_i2c_address(orig_addr)

        return i2c_devices


def main():
    device = AtlasI2c()  # creates the I2C port object,
    # specify the address or bus if necessary
    print(">> Atlas Scientific sample code")
    print(">> Any commands entered are passed to the board via I2C except:")
    print(">> Address,xx changes the I2C address the Raspberry Pi "
          "communicates with.")
    print(">> Poll,xx.x command continuously polls the board every "
          "xx.x seconds")
    print(" where xx.x is longer than the {} second timeout.".format(AtlasI2c.long_timeout))
    print(" Pressing ctrl-c will stop the polling")

    # main loop
    while True:
        myinput = input("Enter command: ")
        myinput_upper = myinput.upper()

        if myinput_upper.startswith("LIST_ADDR"):
            devices = device.list_i2c_devices()
            for i in range(len(devices)):
                print(devices[i])

        # address command lets you change which address
        # the Raspberry Pi will poll
        elif myinput_upper.startswith("ADDRESS"):
            addr = int(myinput.split(',')[1])
            device.set_i2c_address(addr)
            print("I2C address set to {}".format(addr))

        # contiuous polling command automatically polls the board
        elif myinput_upper.startswith("POLL"):
            delaytime = float(myinput.split(',')[1])

            # check for polling time being too short,
            # change it to the minimum timeout if too short
            if delaytime < AtlasI2c.long_timeout:
                print("Polling time is shorter than timeout, "
                      "setting polling time to {}".
                      format(AtlasI2c.long_timeout))
                delaytime = AtlasI2c.long_timeout

            # get the information of the board you're polling
            info = device.query("I").split(",")[1]
            print("Polling {} sensor every {} seconds, press ctrl-c "
                  "to stop polling".
                  format(info, delaytime))

            try:
                sleep_time = delaytime - AtlasI2c.long_timeout
                while True:
                    print(device.query("R"))

                    time.sleep(sleep_time)
            except KeyboardInterrupt:
                # catches the ctrl-c command, which breaks the loop above
                print("Continuous polling stopped")

        # if not a special keyword, pass commands straight to board
        else:
            try:
                print(device.query(myinput))
            except IOError:
                print("Query failed")


if __name__ == '__main__':
    main()
