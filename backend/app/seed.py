from datetime import date, datetime, timedelta

from .extensions import db
from .models import LeaveBalance, LeaveRequest, LeaveType, User
from .services import ensure_leave_types, working_days

USERS = [
    {
        "key": "admin",
        "name": "Aarav Mehta",
        "email": "admin@leavedesk.in",
        "role": "admin",
        "department": "People Ops",
        "job_title": "HR Lead",
        "joined_on": date(2021, 4, 12),
    },
    {
        "key": "ananya",
        "name": "Ananya Rao",
        "email": "demo@leavedesk.in",
        "role": "employee",
        "department": "Design",
        "job_title": "Product Designer",
        "joined_on": date(2022, 7, 18),
    },
    {
        "key": "rohan",
        "name": "Rohan Iyer",
        "email": "rohan.iyer@leavedesk.in",
        "role": "employee",
        "department": "Engineering",
        "job_title": "Backend Engineer",
        "joined_on": date(2021, 11, 2),
    },
    {
        "key": "meera",
        "name": "Meera Nair",
        "email": "meera.nair@leavedesk.in",
        "role": "employee",
        "department": "Engineering",
        "job_title": "Engineering Manager",
        "joined_on": date(2020, 2, 17),
    },
    {
        "key": "kabir",
        "name": "Kabir Shah",
        "email": "kabir.shah@leavedesk.in",
        "role": "employee",
        "department": "Marketing",
        "job_title": "Growth Lead",
        "joined_on": date(2022, 1, 10),
    },
    {
        "key": "isha",
        "name": "Isha Verma",
        "email": "isha.verma@leavedesk.in",
        "role": "employee",
        "department": "Design",
        "job_title": "UX Researcher",
        "joined_on": date(2023, 3, 6),
    },
    {
        "key": "arjun",
        "name": "Arjun Menon",
        "email": "arjun.menon@leavedesk.in",
        "role": "employee",
        "department": "Finance",
        "job_title": "Financial Analyst",
        "joined_on": date(2021, 9, 27),
    },
    {
        "key": "sneha",
        "name": "Sneha Kulkarni",
        "email": "sneha.kulkarni@leavedesk.in",
        "role": "employee",
        "department": "People Ops",
        "job_title": "Recruiter",
        "joined_on": date(2023, 8, 14),
    },
    {
        "key": "vikram",
        "name": "Vikram Singh",
        "email": "vikram.singh@leavedesk.in",
        "role": "employee",
        "department": "Operations",
        "job_title": "IT Administrator",
        "joined_on": date(2022, 5, 23),
    },
    {
        "key": "priya",
        "name": "Priya Deshpande",
        "email": "priya.deshpande@leavedesk.in",
        "role": "employee",
        "department": "Marketing",
        "job_title": "Content Strategist",
        "joined_on": date(2024, 1, 8),
    },
]


def seed():
    if User.query.filter_by(email="demo@leavedesk.in").first():
        print("Demo data already exists, skipping.")
        return

    leave_types = {item.code: item for item in ensure_leave_types()}
    users = {}
    for item in USERS:
        user = User(
            name=item["name"],
            email=item["email"],
            role=item["role"],
            department=item["department"],
            job_title=item["job_title"],
            joined_on=item["joined_on"],
        )
        user.set_password("admin1234" if item["role"] == "admin" else "demo1234")
        db.session.add(user)
        users[item["key"]] = user
    db.session.flush()

    today = date.today()
    year = today.year
    this_monday = today - timedelta(days=today.weekday())

    for user in users.values():
        for leave_type in leave_types.values():
            db.session.add(
                LeaveBalance(
                    user_id=user.id,
                    leave_type_id=leave_type.id,
                    year=year,
                    allocated_days=leave_type.default_days,
                    used_days=0,
                )
            )
    db.session.flush()

    def monday(offset_weeks):
        return this_monday + timedelta(weeks=offset_weeks)

    sequence = 0

    def make_request(key, type_code, start, end, status, reason, note=None):
        nonlocal sequence
        user = users[key]
        leave_type = leave_types[type_code]
        days = working_days(start, end)
        anchor = min(start - timedelta(days=9), today - timedelta(days=3))
        created_at = datetime.combine(anchor, datetime.min.time()).replace(
            hour=10, minute=15
        ) + timedelta(minutes=sequence * 7)
        sequence += 1
        reviewed_at = None
        if status in ("approved", "rejected"):
            reviewed_at = min(
                created_at + timedelta(days=1, hours=3),
                datetime.combine(today, datetime.min.time()).replace(
                    hour=11, minute=45
                ),
            )

        leave_request = LeaveRequest(
            user_id=user.id,
            leave_type_id=leave_type.id,
            start_date=start,
            end_date=end,
            days=days,
            reason=reason,
            status=status,
            reviewed_by_id=users["admin"].id if reviewed_at else None,
            reviewed_at=reviewed_at,
            review_note=note,
            created_at=created_at,
            updated_at=reviewed_at or created_at,
        )
        db.session.add(leave_request)
        return leave_request

    requests = [
        make_request(
            "ananya",
            "EARNED",
            monday(-6),
            monday(-6) + timedelta(days=4),
            "approved",
            "Family holiday in Coorg. Flights and stay are booked.",
            "Approved. Enjoy the break.",
        ),
        make_request(
            "ananya",
            "CASUAL",
            monday(-4) + timedelta(days=3),
            monday(-4) + timedelta(days=4),
            "approved",
            "Moving into a new apartment this weekend.",
        ),
        make_request(
            "ananya",
            "SICK",
            monday(-2),
            monday(-2) + timedelta(days=2),
            "rejected",
            "Down with fever and body ache since Sunday night.",
            "Please attach a medical note for sick leave beyond two days.",
        ),
        make_request(
            "ananya",
            "CASUAL",
            monday(-8),
            monday(-8) + timedelta(days=1),
            "cancelled",
            "Personal errand that was later rescheduled.",
        ),
        make_request(
            "ananya",
            "CASUAL",
            monday(4),
            monday(4) + timedelta(days=1),
            "pending",
            "Cousin's wedding in Hyderabad. Travel on Friday evening.",
        ),
        make_request(
            "ananya",
            "EARNED",
            monday(8),
            monday(8) + timedelta(days=4),
            "approved",
            "Year-end break with family. Booked the train tickets.",
            "Approved. Hand over the design review before you leave.",
        ),
        make_request(
            "rohan",
            "SICK",
            monday(-1),
            monday(-1) + timedelta(days=1),
            "approved",
            "Food poisoning. Working from home is not possible today.",
        ),
        make_request(
            "rohan",
            "CASUAL",
            monday(1),
            monday(1),
            "approved",
            "Passport appointment at the regional office.",
        ),
        make_request(
            "rohan",
            "EARNED",
            monday(2),
            monday(2) + timedelta(days=2),
            "pending",
            "Short trip to Goa with friends.",
        ),
        make_request(
            "meera",
            "EARNED",
            monday(7),
            monday(7) + timedelta(days=3),
            "approved",
            "Family visit during the school winter break.",
            "Approved. Please leave the release checklist with Rohan.",
        ),
        make_request(
            "meera",
            "CASUAL",
            monday(-5),
            monday(-5) + timedelta(days=1),
            "rejected",
            "Looking for an extended weekend.",
            "That is our sprint release week. Please pick another date.",
        ),
        make_request(
            "kabir",
            "SICK",
            monday(-3) + timedelta(days=2),
            monday(-3) + timedelta(days=2),
            "approved",
            "Migraine. Taking the day off to rest.",
        ),
        make_request(
            "kabir",
            "CASUAL",
            monday(3),
            monday(3) + timedelta(days=1),
            "pending",
            "Cousin's engagement ceremony in Pune.",
        ),
        make_request(
            "kabir",
            "EARNED",
            monday(5),
            monday(5) + timedelta(days=2),
            "approved",
            "Trip to Rajasthan with college friends.",
            "Approved. Share the campaign handover doc.",
        ),
        make_request(
            "isha",
            "EARNED",
            monday(0),
            monday(0) + timedelta(days=2),
            "approved",
            "Recovering from a minor dental procedure.",
            "Approved. Take care and rest well.",
        ),
        make_request(
            "isha",
            "EARNED",
            monday(6),
            monday(6) + timedelta(days=1),
            "pending",
            "Wedding shopping with my sister.",
        ),
        make_request(
            "isha",
            "CASUAL",
            monday(-7),
            monday(-7),
            "approved",
            "Building society inspection at home.",
        ),
        make_request(
            "arjun",
            "EARNED",
            monday(6),
            monday(6) + timedelta(days=4),
            "pending",
            "Annual family vacation to Kerala.",
        ),
        make_request(
            "arjun",
            "CASUAL",
            monday(-2) + timedelta(days=2),
            monday(-2) + timedelta(days=2),
            "approved",
            "Bank paperwork for a home loan.",
        ),
        make_request(
            "arjun",
            "SICK",
            monday(-9),
            monday(-9) + timedelta(days=1),
            "approved",
            "Viral fever. Doctor advised two days of rest.",
        ),
        make_request(
            "sneha",
            "SICK",
            monday(-1) + timedelta(days=3),
            monday(-1) + timedelta(days=3),
            "approved",
            "Doctor appointment and follow-up tests.",
        ),
        make_request(
            "sneha",
            "CASUAL",
            monday(1) + timedelta(days=1),
            monday(1) + timedelta(days=1),
            "pending",
            "Parent-teacher meeting at my daughter's school.",
        ),
        make_request(
            "sneha",
            "EARNED",
            monday(8),
            monday(8) + timedelta(days=2),
            "approved",
            "Christmas week break with family.",
            "Approved. Please close the hiring pipeline updates first.",
        ),
        make_request(
            "vikram",
            "EARNED",
            monday(5),
            monday(5) + timedelta(days=2),
            "approved",
            "Hometown visit. Tickets are confirmed.",
            "Approved. Set up the on-call rotation before you leave.",
        ),
        make_request(
            "vikram",
            "CASUAL",
            today,
            today,
            "rejected",
            "Personal work at the bank.",
            "Month-end stock audit that day. Please reschedule.",
        ),
        make_request(
            "priya",
            "CASUAL",
            today,
            today,
            "approved",
            "Sister's engagement ceremony.",
            "Approved. Congratulations to your sister!",
        ),
        make_request(
            "priya",
            "EARNED",
            monday(1) + timedelta(days=3),
            monday(1) + timedelta(days=4),
            "pending",
            "Diwali travel to my parents' place.",
        ),
        make_request(
            "priya",
            "SICK",
            monday(-4) + timedelta(days=1),
            monday(-4) + timedelta(days=1),
            "rejected",
            "Not feeling well today.",
            "Please add a little more detail and resubmit.",
        ),
    ]

    db.session.flush()

    for request in requests:
        if request.status == "approved":
            balance = LeaveBalance.query.filter_by(
                user_id=request.user_id,
                leave_type_id=request.leave_type_id,
                year=request.start_date.year,
            ).first()
            if balance is not None:
                balance.used_days += request.days

    db.session.commit()
    print("Seeded 10 users, 3 leave types, balances, and 28 requests.")
    print("Employee login: demo@leavedesk.in / demo1234")
    print("Admin login: admin@leavedesk.in / admin1234")
