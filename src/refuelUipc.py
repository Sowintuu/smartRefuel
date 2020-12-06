import pyuipc


class VoiceAtis:
    OFFSETS = [(0x0366, 'b'),  # onGroundFlag
               (0x034E, 'H'),  # com1freq
               (0x3118, 'H'),  # com2freq
               (0x3122, 'b'),  # radioActive
               (0x0560, 'l'),  # ac Latitude
               (0x0568, 'l'),  # ac Longitude
               (0x0350, 'H'),  # nav1freq
               (0x0352, 'H'),  # nav2freq
               ]

    def __init__(self):
        # Intialise Pyuipc properties.
        self.pyuipc_connection = None
        self.pyuipc_offsets = None

        # Initialise state properties.
        self.onGround = 0


        self.connect_pyuipc()

    def connect_pyuipc(self):
        try:
            self.pyuipc_connection = pyuipc.open(0)
            self.pyuipc_offsets = pyuipc.prepare_data(self.OFFSETS)
            print('FSUIPC connection established.')
            return True
        except NameError:
            self.pyuipc_connection = None
            print('Error using PYUIPC.')
            return False
        except:
            print('FSUIPC: No simulator detected. Start you simulator first!')
            return False

    def getPyuipcData(self):
        # Read data.
        results = pyuipc.read(self.pyuipcOffsets)

        # Write data to properties.
        self. onGround = results[0]



if __name__ == '__main__':
    pass
