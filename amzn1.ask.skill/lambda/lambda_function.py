# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

import os
from dotenv import load_dotenv
from pymongo import MongoClient
import unidecode

load_dotenv(os.path.join(os.getcwd(), '.env'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PriceCurrentIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("PriceCurrentIntent")(handler_input)

    def handle(self, handler_input):
        
        slots = handler_input.request_envelope.request.intent.slots
        title_arg = slots['title'].value
        title_type_arg = slots['title_type'].value
        site_arg = slots['site'].value
        logger.info('Slots received: title=<{}>, title_type=<{}>, site=<{}>'.format(title_arg, title_type_arg, site_arg))
        
        title_param, title_type_param, site_param = prepare_query_params(title_arg, title_type_arg, site_arg)
        logger.info('Slots prepared: title=<{}>, title_type=<{}>, site=<{}>'.format(title_param, title_type_param, site_param))
        
        client, col = connect_to_mongodb(site_param)
        result = find_in_mongodb(col, title_param, title_type_param)
        close_mongodb_connection(client, site_param)
        logger.info('Found {} results in MongoDB'.format(len(result)))
        
        if len(result) == 0: 
            if title_type_param: 
                speak_output = 'Não encontrei nada na {} com o título {} em {}.'.format(site_arg, title_param, title_type_param)
            else: 
                speak_output = 'Não encontrei nada na {} com o título {}.'.format(site_arg, title_param)
        
        elif len(result) == 1: 
            movie = result[0]
            title_result = movie.get('title')
            title_type_result = movie.get('title_type')
            price_result = movie.get('price')
            site_result = movie.get('spider_pretty_name')

            if price_result != 'Indisponível': 
                price_result = 'R$ ' + price_result.replace('.', ',')
                speak_output = 'Encontrei na {} o título {}, em {}, por {}.'.format(site_result, title_result, title_type_result, price_result)
            else: 
                speak_output = 'Está indisponível, mas encontrei na {} o título {} em {}.'.format(site_result, title_result, title_type_result)
        
        else: 
            if title_type_param: 
                speak_output = 'Encontrei alguns resultados na {} com o título {} em {}, são eles: '.format(site_arg, title_param, title_type_param)
            else: 
                speak_output = 'Encontrei alguns resultados na {} com o título {}, são eles: '.format(site_arg, title_param)
            
            for movie in result: 
                title_result = movie.get('title')
                title_type_result = movie.get('title_type')
                price_result = movie.get('price')
                
                if price_result != 'Indisponível': 
                    price_result = 'R$ ' + price_result.replace('.', ',')
                    speak_output += '{}, em {}, por {}; '.format(title_result, title_type_result, price_result)
                else: 
                    speak_output += '{}, em {}, mas está indisponível; '.format(title_result, title_type_result)
            
            speak_output = speak_output[:-2] + '.'
            
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class LaunchRequestHandler(AbstractRequestHandler):
    
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speak_output = "Bem-vindo ao Canal do Colecionador!"
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = "Você pode me perguntar por preços de DVDs e Blu-rays na Amazon, Fam DVD, The Originals e Vídeo Pérola."
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        speak_output = "Até mais tarde!"
        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    
    """Handler for Session End."""
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."
        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        speak_output = "Não entendi o que você quis dizer."
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


def prepare_query_params(title, title_type, site): 
    
    site = site.replace(' ', '').replace('.', '')
    site = unidecode.unidecode(site)
    
    if title_type: 
        title_type = title_type.lower().replace(' ', '').replace('.', '').replace('-', '')
        title_type = 'DVD' if title_type == 'dvd' else 'Blu-ray'
        
    return title, title_type, site


def connect_to_mongodb(site): 
    client = MongoClient(os.environ['MONGO_URL'])
    db = client.movies
    col = db[site]
    logger.info('Opened MongoDB connection to <{}>'.format(site))
    return client, col


def close_mongodb_connection(client, site): 
    if client: 
        client.close()
        logger.info('Closed MongoDB connection to <{}>'.format(site))
    else: 
        logger.info('MongoDB connection already closed to <{}>'.format(site))


def find_in_mongodb(col, title, title_type): 
    
    if title_type: 
        db_result = list(col.find({'title': {'$regex': title, '$options': 'i'}, 'title_type': {'$regex': title_type, '$options': 'i'}}))
    else: 
        db_result = list(col.find({'title': {'$regex': title, '$options': 'i'}}))
    
    return list(db_result)


# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

sb = SkillBuilder()

sb.add_request_handler(PriceCurrentIntentHandler())
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
