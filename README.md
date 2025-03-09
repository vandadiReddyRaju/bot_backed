# IDE Mentor Bot

An AI-powered IDE mentor bot that helps users with coding questions and provides intelligent responses based on code context.

## Prerequisites

- Docker
- Docker Compose

## Quick Start

1. Clone the repository:
```bash
git clone <your-repository-url>
cd ide_mentor_bot_script_v1
```

2. Create a `.env` file in the root directory with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

3. Build and run the application using Docker Compose:
```bash
docker-compose up --build
```

The application will be available at:
- Frontend: http://localhost
- Backend API: http://localhost:5000

## Deployment Options

### 1. Deploy on Cloud Platforms

#### AWS Elastic Beanstalk
1. Install the EB CLI
2. Initialize EB project:
```bash
eb init
```
3. Deploy:
```bash
eb deploy
```

#### Google Cloud Run
1. Install Google Cloud SDK
2. Build and push the container:
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/ide-mentor-bot
```
3. Deploy:
```bash
gcloud run deploy ide-mentor-bot --image gcr.io/PROJECT_ID/ide-mentor-bot
```

### 2. Deploy on VPS (Digital Ocean, Linode, etc.)

1. SSH into your server
2. Install Docker and Docker Compose
3. Clone the repository
4. Run:
```bash
docker-compose up -d
```

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `FLASK_ENV`: Set to 'production' for deployment

## Security Considerations

1. Always use HTTPS in production
2. Keep your API keys secure
3. Implement rate limiting
4. Regular security updates

## Maintenance

1. Monitor logs:
```bash
docker-compose logs
```

2. Update containers:
```bash
docker-compose pull
docker-compose up -d
```

3. Backup data:
```bash
docker-compose exec backend python backup.py
```

## Support

For issues and feature requests, please create an issue in the repository.

## License

[Your chosen license]
