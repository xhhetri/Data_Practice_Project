"""Fictional practice cases, explicitly separate from real records and evidence."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def seed_demo(repository):
    if repository.vehicles():
        return
    today = datetime.now(ZoneInfo('Australia/Sydney')).date()
    van = repository.create_vehicle(dict(name='Delivery van · fictional', fuel_grade='Diesel', tank_capacity_l='75'))
    ute = repository.create_vehicle(dict(name='Service ute · fictional', fuel_grade='Unleaded 91', tank_capacity_l='65'))
    rows = []
    for i in range(8):
        day = today - timedelta(days=(7-i)*7)
        rows.append(dict(vehicle_id=van['id'], occurred_at=day.isoformat(), litres='45' if i == 7 else '40',
                         amount='99.00' if i == 7 else '84.00', odometer_km=str(10000+i*500), tank_status='full',
                         reference='DEMO-REPEAT' if i >= 6 else f'DEMO-{i}', vendor='Fictional station', note='Fictional practice record'))
    rows.append(dict(vehicle_id=van['id'], occurred_at=(today-timedelta(days=3)).isoformat(), litres='15', amount='33.00',
                     odometer_km='13300', tank_status='partial', reference='DEMO-PARTIAL', note='Fictional partial fill included in the closing interval'))
    rows.append(dict(vehicle_id=ute['id'], occurred_at=today.isoformat(), litres='75', amount='157.50',
                     tank_status='unknown', reference='DEMO-CAPACITY', note='Fictional case: verify capacity and receipt'))
    repository.import_rows(rows, 'fictional-demo-v1')
