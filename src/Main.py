import time
from refuelUipc import RefuelUipc

fuel_2_add = int(input('Add fuel (in kg): '))

refuel = RefuelUipc()
refuel.get_current_fuel()
refuel.refuel_start(fuel_2_add)
while not refuel.refueling_finished:
    time.sleep(1)
    refuel.refuel_update()

print('Script ended.')
