# Coderr/ Backend Project

![Coderr Logo](assets/logo/logo_coderr.svg)

## Description
Coderr is a modern freelance marketplace backend application built with Django and Django REST Framework. The platform seamlessly connects business users (service providers) with customers, enabling businesses to showcase their services through detailed offers with multiple pricing tiers while allowing customers to order services and provide valuable feedback through reviews.
**Note**: This backend is designed to work together with the Coderr Frontend project (separate repository), which provides a complete web interface built with Vanilla JavaScript.

### Key Features
* **User Management** - Two distinct user types (Business & Customer) with comprehensive profile management
* **Service Offers** - Business users can create detailed service offers with multiple pricing tiers (Basic, Standard, Premium)
* **Order System** - Customers can order services with real-time status tracking
* **Review System** - Customers can rate and review business users
* **Guest Access** - Anonymous users can browse with limited functionality
* **Media Handling** - Full support for profile images and offer images
* **Statistics** - Comprehensive site-wide statistics tracking

### Complete System Architecture
The Coderr platform consists of two main components:

**Backend (this repository)** - Django REST API providing:
* User authentication and authorization
* Database models and business logic
* RESTful API endpoints
* Media file handling
* Administrative interface

**Frontend (separate repository)** - Vanilla JavaScript application providing:
* User interface for all platform features
* Responsive design for desktop and mobile
* Real-time interaction with backend APIs
* Image upload and display capabilities

## Technology Stack
* **Django 5.2.1** - Web framework for rapid development
* **Django REST Framework 3.16.0** - Powerful toolkit for building Web APIs
* **django-cors-headers 4.7.0** - Cross-Origin Resource Sharing (CORS)
* **django-filter 25.1** - Dynamic filtering for querysets
* **Pillow 11.2.1** - Image processing library
* **SQLite** - Default database (configurable for PostgreSQL/MySQL)
* **Token Authentication** - Secure API authentication

## Installation & Setup
### Prerequisites
* Python 3.8+
* pip package manager
* Virtual environment (recommended)

### Installation Steps
#### 1. Clone the repository
    git clone "repository-url"
    cd coderr-backend

#### 2. Create and activate virtual environment
    python -m venv env

#### 2.1 Activate virtual enviroment on Windows
    env\Scripts\activate

#### 2.1 Activate virtual enviroment on macOS/Linux
    source env/bin/activate

#### 3. Install dependencies
    pip install -r requirements.txt

#### 4. Environment Configuration
#### 4.1 Create a .env file
In your project root directory (same folder as manage.py), create a new file called .env

#### 4.2 Generate a SECRET_KEY
Run this command in your terminal (with virtual environment activated): <br>
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" <br>
This will output a secret key like: django-insecure-abc123def456...

#### 4.3 Add configuration to .env file
Open the .env file you created and add these lines:
SECRET_KEY=your-generated-secret-key-here
DEBUG=True

**Example .env file:**
SECRET_KEY=django-insecure-abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx
DEBUG=True

**Important Notes:**

Replace your-generated-secret-key-here with the actual key generated in step 4.2
DEBUG=True enables development mode (never use this in production!)
Do NOT commit the .env file to version control (it should be in your .gitignore)

#### 5. Database Setup
    python manage.py makemigrations
    python manage.py migrate

#### 6. Create Superuser (Optional)
    python manage.py createsuperuser

#### 7. Run Development Server
    python manage.py runserver
The API will be available at http://127.0.0.1:8000/

## API Endpoints
### Authentication Endpoints
* **POST** /api/auth/registration/ - User registration
* **POST** /api/auth/login/ - User login
### Core API Endpoints
* **GET/POST** /api/offers/ - List/Create offers
* **GET/PUT/DELETE** /api/offers/{id}/ - Retrieve/Update/Delete offer
* **GET/POST** /api/orders/ - List/Create orders
* **GET/PUT/DELETE** /api/orders/{id}/ - Retrieve/Update/Delete order
* **GET/POST** /api/reviews/ - List/Create reviews
* **GET** /api/profiles/ - List user profiles
* **GET** /api/base-info/ - Site statistics

## Data Models
### Core Models
* **User** - Django's built-in User model extended with Profile
* **Profile** - User profile with business/customer distinction
* **Offer** - Service offerings created by business users
* **OfferDetail** - Pricing tiers (Basic, Standard, Premium) for each offer
* **Feature** - Features included in each offer detail
* **Order** - Customer orders for specific services
* **Review** - Customer reviews for business users
* **BaseInfo** - Site statistics (singleton model)

### Model Relationships
* User ↔ Profile (OneToOne)
* User → Offers (OneToMany, as creator)
* Offer → OfferDetails (OneToMany)
* OfferDetail → Features (OneToMany)
* User → Orders (as customer and business_user)
* OfferDetail → Orders (OneToMany)
* User → Reviews (as reviewer and business_user)

## Authentication & Permissions
### Authentication Methods
* **Token Authentication** - Primary method for API access
* **Session Authentication** - For browsing API interface
* **Guest Login** - Temporary accounts for anonymous users
### Permission Classes
* **IsAuthenticated** - Requires user authentication
* **IsAuthenticatedOrReadOnly** - Read access for all, write for authenticated
* **IsBusinessUser** - Custom permission for business-specific actions
* **IsCustomerUser** - Custom permission for customer-specific actions

## Configuration
### CORS Settings
The project is configured to accept requests from:
* http://127.0.0.1:5500 (Live Server)
* http://localhost:5500
Update CORS_ALLOWED_ORIGINS in settings.py for production use.

## Development
### Running Tests
    python manage.py test

### Creating Migrations
    python manage.py makemigrations
    python manage.py migrate

### Admin Interface
Access the Django admin at http://127.0.0.1:8000/admin/ with superuser credentials.

### API Browsing
Visit http://127.0.0.1:8000/api/ to explore the API using Django REST Framework's browsable interface.

### Related Repository
The frontend is located in a separate repository:
* Repository Name: Coderr Frontend
* Technology: Vanilla JavaScript (no frameworks)
* Target Audience: Developer Akademie students with backend experience

### Frontend Setup Requirements
#### Prerequisites for Frontend
* This Django backend must be running
* Visual Studio Code with Live Server extension
* Web browser for local development

#### Starting the Frontend
Ensure this backend is running (python manage.py runserver)
Open the frontend project in Visual Studio Code
Right-click on index.html and select "Open with Live Server"
The frontend will be available at http://127.0.0.1:5500 (or similar)

#### Frontend Features
* **User Registration & Login** - Connects to authentication endpoints
* **Service Marketplace** - Displays offers from business users
* **Order Management** - Customers can place and track orders
* **Review System** - Customers can rate business users
* **Profile Management** - User profiles with image uploads
* **Guest Access** - Anonymous browsing capabilities

## License
This project is developed as part of the Developer Akademie curriculum.
**Academic Use Only**: This project is exclusively intended for students of the Developer Akademie and is not released for free use or redistribution. Please respect academic integrity guidelines.

## Support
For questions or issues related to this backend:
* Refer to the project documentation
* Check the Django admin interface for data inspection
* Review API endpoints using the browsable API interface
* Contact the development team or instructors
For frontend-related questions, please refer to the separate frontend repository documentation.