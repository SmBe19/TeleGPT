def message_is_image(message):
    if isinstance(message['content'], list):
        for message_part in message['content']:
            if message_part.get('type') == 'image_url':
                return True
    return False

def message_is_audio(message):
    if isinstance(message['content'], list):
        for message_part in message['content']:
            if message_part.get('type') == 'input_audio':
                return True
    return False
