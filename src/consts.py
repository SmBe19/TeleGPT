SOCKET_NAME = 'telegpt.sock'
MAX_WORKER_IDLE_SECONDS = 60 * 60
DATA_DIR = 'chats'
BASE64_PREFIX = 'data:image/png;base64, '

SYSTEM_MESSAGE = 'You are {assistant_name}, a friendly personal assistant. Answer concisely.'

OPENAI_PREFIX = 'openai/'
OPENAI_SETTING_PREFIX = 'oai_'
OPENAI_IMAGE_MODELS = [
    'openai/gpt-image-1-mini',
    'openai/gpt-image-1.5',
    'openai/gpt-image-2',
]
OPENAI_IMAGE_SETTINGS = {
    'oai_size': ['1024x1024', '1024x1536', '1536x1024'],
    'oai_quality': ['low', 'medium', 'high'],
    'oai_background': ['auto', 'transparent', 'opaque'],
}
DEFAULT_OPENAI_IMAGE_SETTINGS = {
    'oai_size': '1024x1024',
    'oai_quality': 'medium',
    'oai_background': 'auto',
}

DEFAULT_SETTINGS = {
    'chat_model': 'openai/gpt-5.6-luna',
    'image_model': 'openai/gpt-image-2',
    'audio_model': 'openai/gpt-audio-mini',
    'speech_model': 'fish-audio/s2.1-pro-free:free',
    'transcribe_model': 'openai/whisper-large-v3-turbo',
}
DEFAULT_THREAD_SETTINGS = {
    'vision_detail': 'low',
}

HIDDEN_IMAGE_SETTINGS = ['n']
