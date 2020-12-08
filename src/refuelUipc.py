import time
import random

import pyuipc


# - c: 1 byte signed
# - b: 1 byte unsigned
# - h: 2 byte signed
# - H: 2 byte unsigned
# - d: 4 byte signed
# - u: 4 byte unsigned
# - l: 8 byte signed
# - L: 8 byte unsigned
# - f: 8 byte floating

class RefuelUipc:
    OFFSETS = [(0x0366, 'b'),  # 0:   onGroundFlag
               (0x0AF4, 'H'),  # 1:   Fuel weight as pounds per gallon * 256
               (0x0B74, 'u'),  # 2/0: centre tank level, % * 128 * 65536        | right wing
               (0x0B78, 'u'),  # 3/0: centre tank capacity: US Gallons
               (0x0B7C, 'u'),  # 4/1: left main tank level, % * 128 * 65536     | left wing
               (0x0B80, 'u'),  # 5/1: left main tank capacity: US Gallons
               (0x0B84, 'u'),  # 6/2: left aux tank level, % * 128 * 65536      | center
               (0x0B88, 'u'),  # 7/2: left aux tank capacity: US Gallons
               (0x0B8C, 'u'),  # 8/3: left tip tank level, % * 128 * 65536      | x
               (0x0B90, 'u'),  # 9/3: left tip tank capacity: US Gallons
               (0x0B94, 'u'),  # 10/4: right main tank level, % * 128 * 65536   | wing tip
               (0x0B98, 'u'),  # 11/4: right main tank capacity: US Gallons
               (0x0B9C, 'u'),  # 12/5: right aux tank level, % * 128 * 65536    | wing tip
               (0x0BA0, 'u'),  # 13/5: right aux tank capacity: US Gallons
               (0x0BA4, 'u'),  # 14/6: right tip tank level, % * 128 * 65536    | x
               (0x0BA8, 'u'),  # 15/6: right tip tank capacity: US Gallons
               ]

    N_TANKS = 7
    REFUELING_RATE = 13  # kg/s ~ 780 kg/min
    REFUELING_ORDER = [[4, 5], [0, 1], [2]]
    REFUEL_ERROR_MAX = 0.02  # 2%

    def __init__(self):
        # Initialise Pyuipc properties.
        self.pyuipc_connection = None
        self.pyuipc_offsets = None

        # Initialise fuel properties.
        self.fuel_pound_gallon = 0.0
        self.fuel_kg_gallon = 0.0
        self.fuel_level_total = 0.0
        self.fuel_capacity_total = 0.0

        self.fuel_levels_kg = [0.0] * self.N_TANKS
        self.fuel_capacity_kg = [0.0] * self.N_TANKS

        # Initialise other properties.
        self.onGround = 0
        self.refueling_started = False
        self.refueling_start_time = 0.0
        self.refueling_finished = False
        self.refueling_levels_start = [0.0] * self.N_TANKS
        self.refueling_target_fuel = 0.0
        self.refueling_fuel_to_add = 0.0
        self.refueling_error = 0.0

        # Connect pyuipc.
        # Sim must be started.
        self.connect_pyuipc()

        # Update fuel status initially.
        self.get_current_fuel()

    # Starts the refueling process.
    # Update methods must be called afterwards to actually update the fuel quantity.
    def refuel_start(self, target_fuel):
        # Check if aircraft is on ground.
        if not self.onGround:
            print('Aircraft is not on ground.')
            return
        # TODO: Check if aircraft is stationary.

        # Print message.
        print('Starting refuel.')

        # Update fuel status at start of refueling.
        self.get_current_fuel()

        # Set target fuel.
        # If more than total capacity, set to total capacity.
        if target_fuel < self.fuel_capacity_total:
            self.refueling_target_fuel = target_fuel
        else:
            self.refueling_target_fuel = self.fuel_capacity_total

        # Get data at fueling start.
        self.refueling_start_time = time.time()
        self.refueling_started = True
        self.refueling_finished = False

        self.refueling_levels_start = self.fuel_levels_kg.copy()

        # Calculate fuel to add.
        # Reduce fuel by some amount.
        self.refueling_error = random.random() * self.REFUEL_ERROR_MAX * self.refueling_target_fuel
        self.refueling_fuel_to_add = self.refueling_target_fuel - sum(self.fuel_levels_kg) - self.refueling_error

    def refuel_update(self):
        # Check if refueling started already.
        if not self.refueling_started:
            print('No refueling started.')
            return

        # Check if refueling finished already.
        if self.refueling_finished:
            print('Refueling finished.')
            return

        # Get elapsed time in seconds and fuel already refueled.
        timeElapsed = time.time() - self.refueling_start_time
        fuel_added = self.REFUELING_RATE * timeElapsed

        # Check if refueling target reached and set stop flag
        stop_refueling = False
        if fuel_added > self.refueling_fuel_to_add:
            fuel_added = self.refueling_fuel_to_add
            stop_refueling = True

        # Copy fuel_added to other variable to work with.
        fuel_added_remaining = fuel_added

        # Update tanks.
        # Loop over refueling order.
        for order in self.REFUELING_ORDER:
            # Get fuel missing to full capacity in current order.
            fuel_missing_order = 0.0
            n_tanks_order = len(order)

            # Get loop over tanks in order to get fuel missing to full.
            for tank in order:
                fuel_missing_order += self.fuel_capacity_kg[tank] - self.refueling_levels_start[tank]

            # Check if fuel to be added until now is bigger than order missing amount.
            if fuel_missing_order < fuel_added_remaining:
                fuel_add_order = fuel_missing_order
            else:
                fuel_add_order = fuel_added_remaining

            # Reduce fuel added remaining.
            fuel_added_remaining -= fuel_add_order

            # Loop over tanks of order to add fuel.
            for tank in order:
                self.fuel_levels_kg[tank] = self.refueling_levels_start[tank] + fuel_add_order / n_tanks_order

        # Update fuel in simulator.
        self.update_fuel()
        print('Fuel added: {} kg'.format(int(fuel_added)))

        # Stop if fuel is reached.
        if stop_refueling:
            self.refueling_finished = True
            print('Refueling finished.')
            return

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
        except pyuipc.FSUIPCException:
            print('FSUIPC: No simulator detected. Start you simulator first!')
            return False

    def get_current_fuel(self):
        # Read data.
        results = pyuipc.read(self.pyuipc_offsets)

        # Write on Ground flag.
        self.onGround = results[0]

        # Get fuel density.
        self.fuel_pound_gallon = results[1] / 256
        self.fuel_kg_gallon = self.fuel_pound_gallon / 2.20462

        # Initialise fuel properties.
        fuel_levels = [0.0] * self.N_TANKS
        fuel_capacity_gal = [0.0] * self.N_TANKS
        self.fuel_levels_kg = [0.0] * self.N_TANKS
        self.fuel_capacity_kg = [0.0] * self.N_TANKS

        # Get fuel for each tank.
        for lvl in range(self.N_TANKS):
            fuel_levels[lvl] = results[2 + lvl * 2] / 8388608
            fuel_capacity_gal[lvl] = results[3 + lvl * 2]
            self.fuel_capacity_kg[lvl] = fuel_capacity_gal[lvl] * self.fuel_kg_gallon
            self.fuel_levels_kg[lvl] = round(fuel_levels[lvl] * self.fuel_capacity_kg[lvl])
            # print('Tank {}: {}'.format(lvl, self.fuel_levels_kg[lvl]))

        # Get total fuel in kg.
        self.fuel_capacity_total = sum(self.fuel_capacity_kg)
        self.fuel_level_total = sum(self.fuel_levels_kg)

        pass

    def update_fuel(self):
        # Initialise list for data writing.
        data_out = []

        # Get fuel level in % and add to out data.
        fuel_levels = [0.0] * self.N_TANKS
        for lvl in range(self.N_TANKS):
            if self.fuel_capacity_kg[lvl] > 0.1:
                fuel_levels[lvl] = int(self.fuel_levels_kg[lvl] / self.fuel_capacity_kg[lvl] * 8388608)
            else:
                fuel_levels[lvl] = 0
            lvl_offsets = self.OFFSETS[2 + lvl * 2]
            data_out.append((lvl_offsets[0], lvl_offsets[1], fuel_levels[lvl]))

        # Write data to simulator.
        pyuipc.write(data_out)


if __name__ == '__main__':
    pass
