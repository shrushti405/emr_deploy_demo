from fastapi import FastAPI, HTTPException,APIRouter,Depends,status
from pydantic import BaseModel
from datetime import date,datetime
from typing import Optional,Annotated
from .models import AppointmentCreate,PatientCreate,Patients,Appointments,AppointmentUpdate,Patientupdate,Defaultschedule,DefaultscheduleCreate,Checavailability,Doctors,Appointment_filter,CreateDoctor
from .database import get_session,engine
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError


def get_session():
    with Session(engine) as sess:
        yield sess

router = APIRouter()
sess = Annotated[Session,Depends(get_session)]




# #creating appointment  while creating appointment if new patient is there add patient details too or else just create appointment for existing patient
# @router.post("/create_appointment")
# def create_appointment(appointment: AppointmentCreate, session: sess):
#     # check if the patient exisits 
#     patient = session.exec(select(Patients).where(Patients.name == appointment.patient_name and Patients.phone_number==appointment.phone_number)).first()
#     if not patient:
#         # create new patient
#         new_patient = Patients(name=appointment.patient_name,phone_number=appointment.phone_number)
#         session.add(new_patient)
#         session.commit()
#         session.refresh(new_patient)
#         patient_id = new_patient.p_id
#     else:
#         patient_id = patient.p_id
#     # create appointment
#     new_appointment = Appointments(
#         patient_id=patient_id,
#         doctor_id=appointment.doctor_id,
#         date=appointment.date,
#         time=appointment.time,
#         status=appointment.status
#     )
#     session.add(new_appointment)
#     session.commit()
#     session.refresh(new_appointment)
#     return {"message": "Appointment created successfully", "appointment_id": new_appointment.a_id}





@router.post("/create_appointment", status_code=status.HTTP_201_CREATED)
def create_appointment(appointment: AppointmentCreate, session: sess):

    try:
        # 1️⃣ Check if patient exists
        patient = session.exec(
            select(Patients).where(
                Patients.phone_number == appointment.phone_number
            )
        ).first()

        if not patient:
            patient = Patients(
                name=appointment.patient_name,
                phone_number=appointment.phone_number
            )
            session.add(patient)
            session.commit()
            session.refresh(patient)

        # 2️⃣ Check appointment time conflict
        existing_appointment = session.exec(
            select(Appointments).where(
                Appointments.doctor_id == appointment.doctor_id,
                Appointments.date == appointment.date,
                Appointments.time == appointment.time
            )
        ).first()

        if existing_appointment:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This time slot is already booked for the doctor"
            )

        # 3️⃣ Create appointment
        new_appointment = Appointments(
            patient_id=patient.p_id,
            doctor_id=appointment.doctor_id,
            date=appointment.date,
            time=appointment.time,
            status=appointment.status
        )

        session.add(new_appointment)
        session.commit()
        session.refresh(new_appointment)

        return {
            "message": "Appointment created successfully",
            "appointment_id": new_appointment.a_id
        }

    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Database constraint violation"
        )

    except HTTPException:
        session.rollback()
        raise

    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

#appointment update and  status update  
@router.patch("/appointments/update")
def update_appointment(appupdate:AppointmentUpdate,session:sess):
    appointment = session.get(Appointments,appupdate.a_id)
    if not appointment:
        raise HTTPException(status_code=404,detail="Appointment not found")
    if appupdate.date:
        appointment.date=appupdate.date
    if appupdate.time:
        appointment.time=appupdate.time
    if appupdate.status:
        appointment.status=appupdate.status
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return {"message":"Appointment updated successfully","appointment":appointment}
    

    
    # Sort by date proximity (closest to today first), then by time
    today = date.today()
    def sort_key(appt):
        appt_date = appt.date
        days_diff = abs((appt_date - today).days)
        return (days_diff, appt.date, appt.time)
    
    appointments.sort(key=sort_key)
    
    return appointments

#patient update 
@router.patch("/patients/update")
def update_patient(patupdate:Patientupdate,session:sess):
    patient = session.get(Patients,patupdate.p_id)
    if not patient:
        raise HTTPException(status_code=404,detail="Patient not found")
    if patupdate.name:
        patient.name=patupdate.name
    if patupdate.date_of_birth:
        patient.date_of_birth=patupdate.date_of_birth
    if patupdate.email:
        patient.email=patupdate.email
    if patupdate.phone_number:
        patient.phone_number=patupdate.phone_number
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return {"message":"Patient updated successfully","patient":patient}
#default schedule creation

@router.post("/default_schedule/create",status_code=status.HTTP_201_CREATED)
def create_default_schedule(defaultschedule:DefaultscheduleCreate,session:sess):
    new_schedule=Defaultschedule(
        doctor_id=defaultschedule.doctor_id,
        strt_time=defaultschedule.strt_time,
        end_time=defaultschedule.end_time,
        datee=defaultschedule.datee,
        status='unavailable',
        work=defaultschedule.work
    )
    session.add(new_schedule)
    session.commit()
    session.refresh(new_schedule)
    return {"message":"Default schedule created successfully","schedule_id":new_schedule.id}


@router.get("/default_schedule/events/{datee}")
def get_default_schedule(datee:str,session:sess):
    schedules=session.exec(select(Defaultschedule).where(Defaultschedule.datee==datee)).all()
    return schedules


#check avaailability of appointment 
@router.post("/appointments/availability")
def check_appointment_availability(checkavailability:Checavailability,session:sess):
    # Check if there's an existing appointment for the doctor at the given date and time
    existing_appointment = session.exec(
        select(Appointments).where(
            Appointments.doctor_id == checkavailability.doctor_id,
            Appointments.date == checkavailability.datee,
            Appointments.time == checkavailability.time
        )
    ).first()

    if existing_appointment:
        return {"available": False, "message": "The time slot is already booked."}
    else:
        return {"available": True, "message": "The time slot is available."}

#get all the appoitments and joinpatient id wihth patient details and doctor id with doctor details
@router.post("/appointments/all")
def get_all_appointments(
    session: sess,
    filterr: Optional[Appointment_filter] = None
):
    # 1️⃣ Base query
    query = (
        select(Appointments, Patients, Doctors)
        .join(Patients, Appointments.patient_id == Patients.p_id)
        .join(Doctors, Appointments.doctor_id == Doctors.d_id)
    )

    # 2️⃣ Apply filters
    if filterr:
        if filterr.date:
            # Convert filter date to string if it's a date object
            if isinstance(filterr.date, date):
                print( "filterr.date is date object", filterr.date)
                filter_date_str = filterr.date.strftime("%Y-%m-%d")
                query = query.where(Appointments.date == filter_date_str)
            else:
                query = query.where(Appointments.date == filterr.date)
        
        if filterr.doctor_id:
            query = query.where(Appointments.doctor_id == filterr.doctor_id)

        if filterr.status:
            query = query.where(Appointments.status == filterr.status)

    # 3️⃣ Execute
    results = session.exec(query).all()

    # 4️⃣ Build response - keep dates as strings
    appointments_list = []
    for appointment, patient, doctor in results:
        # Ensure date is a string
        date_str = str(appointment.date)
        
        appointments_list.append({
            "appointment_id": appointment.a_id,
            "date": date_str,  # Keep as string
            "time": appointment.time,
            "status": appointment.status,
            "patient_name": patient.name,
            "patient_phone": patient.phone_number,
            "doctor_name": doctor.name
        })

    # 5️⃣ Sort by closest date → time
    today_str = date.today().strftime("%Y-%m-%d")
    
    def days_from_today(date_str):
        """Calculate days difference between date string and today"""
        try:
            # Parse string to date object for comparison
            appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today_date = date.today()
            return abs((appt_date - today_date).days)
        except (ValueError, TypeError):
            # If date format is invalid, put it at the end
            return float('inf')

    appointments_list.sort(
        key=lambda appt: (
            days_from_today(appt["date"]),  # Sort by proximity to today
            appt["date"],  # Then by date string (chronological)
            appt["time"]   # Then by time
        )
    )

    # 6️⃣ Dates are already strings, no conversion needed
    return appointments_list
@router.get("/appointments/today_date")
def get_today_appointments(numm: int, session: sess):
    from sqlalchemy import select
    
    today = date.today()
    print(f"Today's date: {today}")
    print(f"Numm parameter: {numm}")
    
    # Join all three tables correctly
    query = select(
        Appointments, 
        Patients.name, 
        Doctors.name,
        Patients.phone_number,
        Patients.email
    ).join(
        Patients, Appointments.patient_id == Patients.p_id
    ).join(
        Doctors, Appointments.doctor_id == Doctors.d_id
    )
    
    results = session.exec(query).all()
    print(f"Total results from query: {len(results)}")
    
    filtered_appointments = []
    
    for appt, patient_name, doctor_name, patient_phone, patient_email in results:
        print(f"\nProcessing appointment ID: {appt.a_id}")
        print(f"Appointment date type: {type(appt.date)}")
        print(f"Appointment date value: {appt.date}")
        print(f"Patient: {patient_name}, Doctor: {doctor_name}")
        
        # appt.date is already a date object (based on the error)
        appt_date = appt.date
        
        should_include = False
        
        if numm == 1:  # Past appointments
            if appt_date < today:
                should_include = True
                print(f"PAST: {appt_date} < {today} = {appt_date < today}")
        elif numm == 2:  # Today's appointments
            if appt_date == today:
                should_include = True
                print(f"TODAY: {appt_date} == {today} = {appt_date == today}")
        elif numm == 3:  # Upcoming appointments
            if appt_date > today:
                should_include = True
                print(f"UPCOMING: {appt_date} > {today} = {appt_date > today}")
        else:  # Invalid numm, return all
            should_include = True
            print(f"ALL: including all appointments")
        
        if should_include:
            appointment_data = {
                "appointment_id": appt.a_id,
                "patient_id": appt.patient_id,
                "doctor_id": appt.doctor_id,
                "date": appt_date.isoformat() if hasattr(appt_date, 'isoformat') else str(appt_date),
                "time": appt.time,
                "status": appt.status,
                "patient_name": patient_name,
                "doctor_name": doctor_name,
                "patient_phone": patient_phone,
                "email": patient_email
            }
            filtered_appointments.append(appointment_data)
            print(f"✓ Included appointment ID: {appt.a_id}")
        else:
            print(f"✗ Excluded appointment ID: {appt.a_id}")
    
    print(f"\nTotal filtered appointments: {len(filtered_appointments)}")
    return filtered_appointments
#later it should beimplmented on the basis of today,upcomig,completed
#create doctor
@router.post("/doctor")
def create_doctor(doctor:CreateDoctor,session:sess):
    new_doctor=Doctors(
        name=doctor.name,
        specialization=doctor.specialization,
        email=doctor.email,
        phone_number=doctor.phone_number
    )
    session.add(new_doctor)
    session.commit()
    session.refresh(new_doctor)
    return {"message":"Doctor created successfully","doctor_id":new_doctor.d_id}




# """
# Query appointments with optional filters.

# In a real AWS AppSync + Aurora implementation:
# - This endpoint would map to an AppSync Query resolver
# - The resolver would execute a GraphQL query against Aurora database
# - AppSync would handle authentication, authorization, and request/response mapping
# - Data would be fetched from Amazon Aurora with proper indexing for efficient filtering
#     """
# @router.post("/appointments")
# def get_appointments(filter: Optional[Appointment_filter] = None):
    
#     filtered_appointments = data
#     today = date.today()

#     if filter:
#         if filter.datee:
#             filtered_appointments = [appt for appt in filtered_appointments if appt["date"] == str(filter.datee)]
#         if filter.doctorName:
#             filtered_appointments = [appt for appt in filtered_appointments if appt["doctorName"] == filter.doctorName]
#         if filter.status:
#             filtered_appointments = [appt for appt in filtered_appointments if appt["status"] == filter.status]
    
#     # Sort by date proximity (closest to today first), then by time
#     def sort_key(appt):
#         appt_date = datetime.strptime(appt["date"], "%Y-%m-%d").date()
#         days_diff = abs((appt_date - today).days)
#         return (days_diff, appt["date"], appt["time"])
    
#     filtered_appointments.sort(key=sort_key)
    
#     return filtered_appointments


#     """
#       Update appointment status.
      
#       In a production AWS AppSync + Aurora implementation:
      
#       1. APPSYNC SUBSCRIPTION TRIGGER:
#         - After successful mutation, AppSync would automatically publish the update
#           to all subscribed clients via WebSocket connections
#         - Real-time dashboard updates would be triggered for:
#           * Queue management screens
#           * Doctor's appointment dashboard
#           * Patient status notifications
#         - Subscription topics would be scoped by:
#           * Doctor ID for doctor-specific updates
#           * Clinic ID for clinic-wide updates
      
#       2. AURORA TRANSACTIONAL WRITE:
#         - This would perform an Aurora database transaction with ACID guarantees:
#           * ATOMICITY: Either all operations succeed or none do
#           * CONSISTENCY: Database constraints are maintained
#           * ISOLATION: Concurrent updates don't interfere
#           * DURABILITY: Changes are permanently saved
#         - The transaction would include:
#           * Update appointment status in appointments table
#           * Log the status change in audit_logs table
#           * Update queue_position in queue_management table if needed
#           * Send notification to Amazon SNS/SQS for downstream services
#       """

# @.patch("/appointments/status")
# def update_appointment_status(update: AppointmentStatusUpdate):
#     for appointment in data:
#         if appointment["id"] == update.appointment_id:
#             appointment["status"] = update.new_status
#             return {"message": "Status updated successfully", "appointment": appointment}
    
#     raise HTTPException(status_code=404, detail="Appointment not found")

# Set-ExecutionPolicy unrestricted -Scope Process