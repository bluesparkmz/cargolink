from pathlib import Path
import shutil, sys
from datetime import datetime

ROOT = Path.cwd()
if not (ROOT/'main.py').exists() or not (ROOT/'controllers/trips_controller.py').exists():
    print('ERRO: execute este script na raiz do cargolink_api.')
    sys.exit(1)
BACKUP = ROOT / f"_backup_trip_assignment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def read(rel):
    p=ROOT/rel
    if not p.exists(): raise SystemExit(f'ERRO: ficheiro nao encontrado: {rel}')
    return p.read_text(encoding='utf-8')

def save(rel,text):
    src=ROOT/rel; dst=BACKUP/rel
    dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    src.write_text(text,encoding='utf-8',newline='\n'); print('OK ',rel)

# schema
rel='schemas/schemas.py'; text=read(rel)
if 'class TripAssignVehicleRequest' not in text:
    marker='class TripStartRequest(BaseModel):\n'
    add="class TripAssignVehicleRequest(BaseModel):\n    # Empresa atribui camiao com motorista a uma viagem aceite.\n    vehicle_id: int = Field(..., gt=0)\n\n\n"
    if marker not in text: raise SystemExit('ERRO: TripStartRequest nao encontrado')
    text=text.replace(marker,add+marker,1); save(rel,text)

# trips controller
rel='controllers/trips_controller.py'; text=read(rel)
if 'VEHICLE_STATUS_AVAILABLE' not in text:
    old='    TRIP_STATUS_WAITING_CLIENT,\n)'
    if old not in text: raise SystemExit('ERRO: bloco de constants inesperado')
    text=text.replace(old,'    TRIP_STATUS_WAITING_CLIENT,\n    VEHICLE_STATUS_AVAILABLE,\n)',1)
if 'def assign_vehicle_to_trip(' not in text:
    marker='\ndef start_pickup_trip(db: Session, user: User, trip_id: int) -> Trip:\n'
    if marker not in text: raise SystemExit('ERRO: start_pickup_trip nao encontrado')
    fn="""
def assign_vehicle_to_trip(db: Session, user: User, trip_id: int, vehicle_id: int) -> dict:
    # Empresa atribui camiao e motorista a uma viagem aceite.
    if user.user_type != 'empresa':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Apenas a empresa transportadora pode atribuir o camiao')
    company = db.query(Company).filter(Company.user_id == user.id).first()
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Perfil de empresa nao encontrado')
    trip = get_trip_detail(db, trip_id)
    if trip.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Esta viagem pertence a outra empresa')
    if trip.status != TRIP_STATUS_WAITING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='O camiao so pode ser atribuido antes do motorista iniciar a recolha')

    vehicle = db.query(Vehicle).options(joinedload(Vehicle.driver).joinedload(Driver.user)).filter(Vehicle.id == vehicle_id).first()
    if vehicle is None or vehicle.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Camiao invalido para esta empresa')
    if vehicle.status != VEHICLE_STATUS_AVAILABLE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='O camiao selecionado nao esta disponivel')
    if vehicle.driver_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Este camiao nao tem motorista atribuido. Atribua um motorista antes de usar o camiao nesta carga.')

    driver = vehicle.driver or db.query(Driver).filter(Driver.id == vehicle.driver_id).first()
    if driver is None or driver.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Motorista invalido para este camiao')
    if not driver.available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='O motorista deste camiao nao esta disponivel')

    if db.query(Trip).filter(Trip.id != trip.id, Trip.vehicle_id == vehicle.id, Trip.status != TRIP_STATUS_COMPLETED).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Este camiao ja esta atribuido a outra viagem ativa')
    if db.query(Trip).filter(Trip.id != trip.id, Trip.driver_id == driver.id, Trip.status != TRIP_STATUS_COMPLETED).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='O motorista deste camiao ja esta atribuido a outra viagem ativa')

    trip.vehicle_id = vehicle.id
    trip.driver_id = driver.id
    db.commit(); db.refresh(trip)
    load = db.query(Load).filter(Load.id == trip.load_id).first()
    code = load.code if load else f'#{trip.load_id}'
    rota = f' {load.origin} -> {load.destination}.' if load else ''
    log_trip_activity(db, trip, event_type='trip_assigned', title='Camiao e motorista atribuidos', description=f'Camiao {vehicle.plate} atribuido a viagem.')

    notification = create_notification(db, user_id=driver.user_id, title='Nova carga atribuida', body=f'Foi-lhe atribuida a carga {code}.{rota}', notification_type='trip.assigned', payload={'trip_id':trip.id,'load_id':trip.load_id,'vehicle_id':vehicle.id,'driver_id':driver.id})
    db.commit(); db.refresh(notification); emit_notification(notification)
    emit_to_rooms(_trip_event_rooms(trip), {'type':'trip.assigned','trip_id':trip.id,'load_id':trip.load_id,'company_id':trip.company_id,'driver_id':driver.id,'vehicle_id':vehicle.id,'status':trip.status})
    return _serialize_trip(get_trip_detail(db, trip.id))


"""
    text=text.replace(marker,'\n'+fn+marker.lstrip('\n'),1)
save(rel,text)

# router
rel='routers/trips.py'; text=read(rel)
if 'assign_vehicle_to_trip,' not in text:
    text=text.replace('from controllers.trips_controller import (\n    user_can_access_trip,','from controllers.trips_controller import (\n    assign_vehicle_to_trip,\n    user_can_access_trip,',1)
if 'TripAssignVehicleRequest,' not in text:
    text=text.replace('from schemas.schemas import (\n    TripLocationCreateRequest,','from schemas.schemas import (\n    TripAssignVehicleRequest,\n    TripLocationCreateRequest,',1)
if '/assign-vehicle' not in text:
    marker='@router.patch("/{trip_id}/start-pickup", response_model=TripResponse)\n'
    route="""@router.patch('/{trip_id}/assign-vehicle', response_model=TripResponse)
def assign_vehicle(trip_id: int, data: TripAssignVehicleRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return assign_vehicle_to_trip(db, current_user, trip_id, data.vehicle_id)


"""
    if marker not in text: raise SystemExit('ERRO: rota start-pickup nao encontrada')
    text=text.replace(marker,route+marker,1)
save(rel,text)

# vehicle realtime
rel='controllers/vehicles_controller.py'; text=read(rel)
if 'from controllers.realtime_events import emit_to_user' not in text:
    text=text.replace('from controllers.drivers_controller import get_my_driver\n','from controllers.drivers_controller import get_my_driver\nfrom controllers.realtime_events import emit_to_user\n',1)
old="""    vehicle = Vehicle(company_id=company.id, **payload)
    db.add(vehicle)
    db.commit()
    return get_vehicle_by_id(db, vehicle.id)
"""
new="""    vehicle = Vehicle(company_id=company.id, **payload)
    db.add(vehicle)
    db.commit()
    created = get_vehicle_by_id(db, vehicle.id)
    emit_to_user(user.id, {'type':'vehicle.created','vehicle_id':created.id,'company_id':company.id})
    return created
"""
if old in text: text=text.replace(old,new,1)
old="""    db.commit()
    return get_vehicle_by_id(db, vehicle_id)


def deactivate_vehicle"""
new="""    db.commit()
    updated = get_vehicle_by_id(db, vehicle_id)
    emit_to_user(user.id, {'type':'vehicle.updated','vehicle_id':updated.id,'company_id':company.id,'driver_id':updated.driver_id})
    return updated


def deactivate_vehicle"""
if old in text: text=text.replace(old,new,1)
old="""    vehicle.status = VEHICLE_STATUS_INACTIVE
    db.commit()"""
new="""    vehicle.status = VEHICLE_STATUS_INACTIVE
    db.commit()
    emit_to_user(user.id, {'type':'vehicle.deactivated','vehicle_id':vehicle.id,'company_id':vehicle.company_id})"""
if old in text: text=text.replace(old,new,1)
save(rel,text)

# company driver realtime
rel='controllers/companies_controller.py'; text=read(rel)
if 'from controllers.realtime_events import emit_to_user' not in text:
    text=text.replace('from security import generate_random_password, hash_password\n','from security import generate_random_password, hash_password\nfrom controllers.realtime_events import emit_to_user\n',1)
old="""    driver.company_id = company.id
    db.commit()
    db.refresh(driver)
    return driver
"""
new="""    driver.company_id = company.id
    db.commit()
    db.refresh(driver)
    emit_to_user(user.id, {'type':'driver.attached','driver_id':driver.id,'company_id':company.id})
    return driver
"""
if old in text: text=text.replace(old,new,1)
old="""    _detach_driver_from_company(db, company, driver)


def detach_driver_from_company_by_email"""
new="""    _detach_driver_from_company(db, company, driver)
    emit_to_user(user.id, {'type':'driver.detached','driver_id':driver.id,'company_id':company.id})


def detach_driver_from_company_by_email"""
if old in text: text=text.replace(old,new,1)
old="""    driver = get_company_driver_by_email(db, company, email)
    _detach_driver_from_company(db, company, driver)


def _detach_driver_from_company"""
new="""    driver = get_company_driver_by_email(db, company, email)
    _detach_driver_from_company(db, company, driver)
    emit_to_user(user.id, {'type':'driver.detached','driver_id':driver.id,'company_id':company.id})


def _detach_driver_from_company"""
if old in text: text=text.replace(old,new,1)
old="""    return (
        db.query(Driver)
        .options(joinedload(Driver.user))
        .filter(Driver.id == new_driver.id)
        .first(),
        temporary_password,
    )
"""
new="""    created_driver = (
        db.query(Driver)
        .options(joinedload(Driver.user))
        .filter(Driver.id == new_driver.id)
        .first()
    )
    emit_to_user(user.id, {'type':'driver.created','driver_id':created_driver.id,'company_id':company.id})
    return created_driver, temporary_password
"""
if old in text: text=text.replace(old,new,1)
save(rel,text)

print('BACKEND ACTUALIZADO')
print('Endpoint: PATCH /trips/{trip_id}/assign-vehicle')
print('Backup:',BACKUP)
