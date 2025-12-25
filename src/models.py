from fastapi import FastAPI 
from pydantic import BaseModel
from typing import List,Optional
from datetime import date
from sqlmodel import SQLModel, Field 

class Patients(SQLModel, table=True):
    p_id: int = Field(default=None, primary_key=True) #Field in SQLModel is used to define database-related rules like primary key, default value, uniqueness, and indexing, which plain Python type hints cannot specify
    name: str
    date_of_birth: Optional[date] = None
    email: Optional[str] = None
    phone_number: str

class Doctors(SQLModel, table=True):
    d_id: int = Field(default=None, primary_key=True)
    name: str
    specialization: str
    email: Optional[str] = None
    phone_number: str
class Appointments(SQLModel, table=True):
    a_id: int = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.p_id")
    doctor_id: int = Field(foreign_key="doctors.d_id")
    date: str
    time: str
    status: str  # e.g., "scheduled", "completed", "canceled"
class MedicalRecords(SQLModel, table=True):
    record_id: int = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.p_id")
    doctor_id: int = Field(foreign_key="doctors.d_id")
    appointment_id: int = Field(foreign_key="appointments.a_id")
    diagnosis: str
    treatment: str
    prescriptions: Optional[str] = None

class AppointmentCreate(BaseModel):
    # patient_id: int
    patient_name: str
    doctor_id: int
    date: str
    time: str
    phone_number:str
    status: str  # e.g., "scheduled", "completed", "canceled"
class PatientCreate(BaseModel):
    name: str
    date_of_birth: Optional[date] = None
    email: Optional[str] = None
    phone_number: str

class AppointmentUpdate(BaseModel):
    a_id: int
    date: Optional[str] = None
    time: Optional[str] = None
    status: Optional[str] = None

class Patientupdate(BaseModel):
    p_id: int
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
class Defaultschedule(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    doctor_id: int = Field(foreign_key="doctors.d_id")
    strt_time:str
    end_time:str
    datee:str
    status: str="unavailable"  
    work:Optional[str]=None

class DefaultscheduleCreate(BaseModel):
    doctor_id: int
    strt_time:str
    end_time:str
    datee:str
    work:Optional[str]=None

class Checavailability(BaseModel):
    doctor_id: int
    datee:str
    time:str

class Appointment_filter(BaseModel):
    doctor_id: Optional[int] = None
    
    date: Optional[str] = None
    status: Optional[str] = None

class CreateDoctor(BaseModel):
    name: str
    specialization: str
    email: Optional[str] = None
    phone_number: str