from pathlib import Path
from datetime import datetime
import shutil, sys

ROOT = Path.cwd()
needed = [
    "main.py",
    "schemas/schemas.py",
    "routers/vehicles.py",
    "controllers/loads_controller.py",
    "controllers/proposals_controller.py",
]
missing = [p for p in needed if not (ROOT / p).exists()]
if missing:
    print("ERRO: execute este script na raiz do cargolink_api.")
    print("Em falta:", ", ".join(missing))
    sys.exit(1)

BACKUP = ROOT.parent / f"cargolink_api_backup_manual_assignment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def save(rel, text):
    src = ROOT / rel
    dst = BACKUP / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    src.write_text(text, encoding="utf-8", newline="\n")
    print("OK ", rel)

# 1) Schema dedicado.
rel = "schemas/schemas.py"
text = read(rel)
if "class VehicleDriverAssignmentRequest(BaseModel):" not in text:
    marker = "\n\n# ---------------------------------------------------------------------------\n# Viagens\n# ---------------------------------------------------------------------------\n"
    addition = '''

class VehicleDriverAssignmentRequest(BaseModel):
    # Associa ou remove motorista de um camião da empresa.
    driver_id: int | None = None
'''
    if marker not in text:
        raise SystemExit("ERRO: secção Viagens não encontrada em schemas.py")
    text = text.replace(marker, addition + marker, 1)
save(rel, text)

# 2) Router de veículos.
rel = "routers/vehicles.py"
text = read(rel)

if "VehicleDriverAssignmentRequest," not in text:
    text = text.replace(
        "    VehicleDetailResponse,\n",
        "    VehicleDetailResponse,\n    VehicleDriverAssignmentRequest,\n",
        1,
    )

old = '''    data = VehicleUpdateRequest(
        plate=plate,
        driver_id=driver_id,
        driver_email=driver_email,
        brand=brand,
        model_name=model_name,
        vehicle_type=vehicle_type,
        tonnage_capacity=tonnage_capacity,
        status=status,
    )
'''
new = '''    payload = {
        key: value
        for key, value in {
            "plate": plate,
            "driver_id": driver_id,
            "driver_email": driver_email,
            "brand": brand,
            "model_name": model_name,
            "vehicle_type": vehicle_type,
            "tonnage_capacity": tonnage_capacity,
            "status": status,
        }.items()
        if value is not None
    }
    data = VehicleUpdateRequest(**payload)
'''
if old in text:
    text = text.replace(old, new, 1)

if '@router.patch("/{vehicle_id}/driver"' not in text:
    marker = '@router.patch("/{vehicle_id}", response_model=VehicleListItem)\n'
    endpoint = '''@router.patch("/{vehicle_id}/driver", response_model=VehicleListItem)
def patch_driver(
    vehicle_id: int,
    data: VehicleDriverAssignmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Empresa associa ou remove o motorista de um camião.
    vehicle = update_vehicle(
        db,
        current_user,
        vehicle_id=vehicle_id,
        data=VehicleUpdateRequest(driver_id=data.driver_id),
    )
    return _to_list_item(vehicle)


'''
    if marker not in text:
        raise SystemExit("ERRO: rota PATCH /{vehicle_id} não encontrada")
    text = text.replace(marker, endpoint + marker, 1)

save(rel, text)

# 3) Aceite direto: Trip sem camião e sem motorista.
rel = "controllers/loads_controller.py"
text = read(rel)
old = '''    trip = Trip(
        load_id=load_id,
        company_id=proposal.company_id,
        driver_id=proposal.driver_id,
        vehicle_id=proposal.vehicle_id,
    )
'''
new = '''    # A proposta aceite define apenas a empresa vencedora.
    # O camião e o motorista serão escolhidos manualmente pela empresa.
    trip = Trip(
        load_id=load_id,
        company_id=proposal.company_id,
        driver_id=None,
        vehicle_id=None,
    )
'''
if old in text:
    text = text.replace(old, new, 1)
elif "driver_id=None,\n        vehicle_id=None," not in text:
    raise SystemExit("ERRO: criação de Trip no accept_proposal não encontrada")

driver_target = '''    if proposal.driver_id:
        driver = db.query(Driver).filter(Driver.id == proposal.driver_id).first()
        if driver:
            targets.add(driver.user_id)
'''
if driver_target in text:
    text = text.replace(driver_target, "", 1)

text = text.replace(
    'body=f"A proposta para a carga {load.code} foi aceite. A viagem foi criada.",',
    'body=f"A proposta para a carga {load.code} foi aceite. Atribua um camião para iniciar o transporte.",',
    1,
)

old_rooms = '''        {
            f"load:{load.id}",
            f"trip:{trip.id}",
            f"company:{proposal.company_id}" if proposal.company_id else "",
            f"driver:{proposal.driver_id}" if proposal.driver_id else "",
        }
        - {""},
'''
new_rooms = '''        {
            f"load:{load.id}",
            f"trip:{trip.id}",
            f"company:{proposal.company_id}" if proposal.company_id else "",
        }
        - {""},
'''
if old_rooms in text:
    text = text.replace(old_rooms, new_rooms, 1)

save(rel, text)

# 4) Contraproposta aceite: mesma regra manual.
rel = "controllers/proposals_controller.py"
text = read(rel)
old = '''        Trip(
            load_id=proposal.load_id,
            company_id=proposal.company_id,
            driver_id=proposal.driver_id,
            vehicle_id=proposal.vehicle_id,
        )
'''
new = '''        Trip(
            load_id=proposal.load_id,
            company_id=proposal.company_id,
            driver_id=None,
            vehicle_id=None,
        )
'''
if old in text:
    text = text.replace(old, new, 1)
elif "company_id=proposal.company_id,\n            driver_id=None,\n            vehicle_id=None," not in text:
    raise SystemExit("ERRO: criação de Trip em _close_proposal_as_accepted não encontrada")

if "def _proposal_acceptance_user_ids(" not in text:
    marker = "\ndef _proposal_rooms(proposal: LoadProposal) -> set[str]:\n"
    helper = '''
def _proposal_acceptance_user_ids(db: Session, proposal: LoadProposal) -> set[int]:
    # Cliente + empresa. Motorista só participa após trip.assigned.
    user_ids: set[int] = set()
    load = proposal.load or db.query(Load).filter(Load.id == proposal.load_id).first()
    if load:
        client = db.query(Client).filter(Client.id == load.client_id).first()
        if client:
            user_ids.add(client.user_id)
    if proposal.company_id:
        company = db.query(Company).filter(Company.id == proposal.company_id).first()
        if company:
            user_ids.add(company.user_id)
    return user_ids


def _proposal_acceptance_rooms(proposal: LoadProposal) -> set[str]:
    rooms = {f"load:{proposal.load_id}", f"proposal:{proposal.id}"}
    if proposal.company_id:
        rooms.add(f"company:{proposal.company_id}")
    return rooms

'''
    if marker not in text:
        raise SystemExit("ERRO: _proposal_rooms não encontrado")
    text = text.replace(marker, helper + marker, 1)

start = text.find("def accept_counter_offer(")
end = text.find("\ndef reject_counter_offer(", start)
if start == -1 or end == -1:
    raise SystemExit("ERRO: accept_counter_offer não encontrado")
section = text[start:end]
section = section.replace(
    "for user_id in (_proposal_user_ids(db, proposal) - {user.id})",
    "for user_id in (_proposal_acceptance_user_ids(db, proposal) - {user.id})",
)
section = section.replace(
    "_proposal_rooms(proposal) | ({f\"trip:{trip.id}\"} if trip else set())",
    "_proposal_acceptance_rooms(proposal) | ({f\"trip:{trip.id}\"} if trip else set())",
)
section = section.replace(
    'body="A contraproposta foi aceite e a viagem foi criada.",',
    'body="A contraproposta foi aceite. A empresa deve atribuir um camião para iniciar o transporte.",',
)
text = text[:start] + section + text[end:]
save(rel, text)

print()
print("BACKEND CORRIGIDO")
print("- proposta aceite cria Trip apenas com company_id")
print("- driver_id e vehicle_id ficam NULL")
print("- motorista só recebe notificação em trip.assigned")
print("- novo PATCH /vehicles/{vehicle_id}/driver")
print("- PATCH genérico de veículo deixa de validar status=None")
print("Backup:", BACKUP)
print()
print("Valide:")
print("  python -m compileall controllers routers schemas")
print("  git diff --check")
print("  git status")
