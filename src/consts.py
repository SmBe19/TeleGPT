SOCKET_NAME = 'telegpt.sock'
MAX_WORKER_IDLE_SECONDS = 60 * 60
DATA_DIR = 'chats'
BASE64_PREFIX = 'data:image/png;base64, '

FEAT_VISION = 'vision'
FEAT_AUDIO = 'audio'
FEAT_SPEECH = 'speech'
FEAT_SPEECH_INSTRUCTIONS = 'speech_instructions'
FEAT_EDITS = 'edits'
FEAT_RESPONSE_FORMAT = 'response_format'
FEAT_MODERATION = 'moderation'
IMAGE_SIZES = 'sizes'
IMAGE_QUALITY = 'quality'
IMAGE_STYLE = 'style'
IMAGE_BACKGROUND = 'background'
SPEECH_VOICES = 'voices'

SYSTEM_MESSAGE = 'You are {assistant_name}, a friendly personal assistant. Answer concisely.'
CHAT_MODELS = {
    'gpt-3.5-turbo': {},
    'gpt-4': {},
    'gpt-4-turbo': { FEAT_VISION: True },
    'gpt-4o': { FEAT_VISION: True },
    'gpt-4o-mini': { FEAT_VISION: True },
    'gpt-4o-audio-preview': { FEAT_AUDIO: True, FEAT_SPEECH: True },
    'gpt-4o-mini-audio-preview': { FEAT_AUDIO: True, FEAT_SPEECH: True },
    'gpt-4.1': { FEAT_VISION: True },
    'o3': { FEAT_VISION: True },
    'o4-mini': { FEAT_VISION: True },
}
TRANSCRIBE_MODELS = {
    'whisper-1': {},
    'gpt-4o-transcribe': {},
    'gpt-4o-mini-transcribe': {},
}
SPEECH_MODELS = {
    'tts-1': {
        SPEECH_VOICES: ['echo', 'alloy', 'ash', 'ballad', 'coral', 'fable', 'onyx', 'nova', 'sage', 'shimmer', 'verse'],
    },
    'gpt-4o-mini-tts': {
        FEAT_SPEECH_INSTRUCTIONS: True,
        SPEECH_VOICES: ['echo', 'alloy', 'ash', 'ballad', 'coral', 'fable', 'onyx', 'nova', 'sage', 'shimmer', 'verse'],
    },
}
IMAGE_MODELS = {
    'dall-e-2': {
        IMAGE_SIZES: ['256x256', '512x512', '1024x1024'],
        FEAT_RESPONSE_FORMAT: True,
        FEAT_EDITS: True,
    },
    'dall-e-3': {
        IMAGE_SIZES: ['1024x1024', '1024x1792', '1792x1024'],
        IMAGE_QUALITY: ['standard', 'hd'],
        IMAGE_STYLE: ['natural', 'vivid'],
        FEAT_RESPONSE_FORMAT: True,
    },
    'gpt-image-1': {
        IMAGE_SIZES: ['1024x1024', '1024x1536', '1536x1024'],
        IMAGE_QUALITY: ['low', 'medium', 'high'],
        IMAGE_BACKGROUND: ['auto', 'transparent', 'opaque'],
        FEAT_EDITS: True,
        FEAT_MODERATION: True,
    },
}
DEFAULT_CHAT_MODEL = 'gpt-4o-mini'
DEFAULT_TRANSCRIBE_MODEL = 'whisper-1'
DEFAULT_SPEECH_MODEL = 'tts-1'
DEFAULT_IMAGE_MODEL = 'gpt-image-1'
