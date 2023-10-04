import env_variables
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey

db_url = env_variables.SQL_URI
engine = create_engine(db_url, echo=False)  # Set echo=True for debugging SQL statements
Base = declarative_base()

class ApiAccount(Base):
    __tablename__ = "api_account"
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(50), index=True)
    tasks = relationship("Task", back_populates="api_account")

class Task(Base):
    __tablename__ = "task"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(30), index=True)
    result = Column(String(100), index=True)
    state = Column(String(20), index=True)
    api_account_id = Column(Integer, ForeignKey("api_account.id"))
    api_account = relationship("ApiAccount", back_populates="tasks")

Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
