"""
NODIS Token Smart Contract
===================================

Authors: Nathan Mukena & Dominic Fung
Emails: nathan.mukena@nodis.io & dominic.fung@nodis.io

Date: March 15 2019

"""
from nodis.txio import get_asset_attachments
from nodis.token import *
from nodis.crowdsale import *
from nodis.nep5 import *
from nodis.mining import handle_mining
from boa.interop.Neo.Runtime import GetTrigger, CheckWitness, Log, Notify, GetTime
from boa.interop.Neo.TriggerType import Application, Verification
from boa.interop.Neo.Storage import *
from boa.interop.Neo.Blockchain import Migrate, Destroy

ctx = GetContext()
NEP5_METHODS = ['name', 'symbol', 'decimals', 'totalSupply', 'balanceOf', 'transfer', 'transferFrom', 'approve', 'allowance']
MINING_METHODS = ['register_business', 'check_business', 'signout_business', 'create_challenge', 'close_challenge', 'submit', 'approve_submission', 'reject_submission', 'promoter_claim', 'approver_claim', 'rejecter_claim', 'get_mining_rate', 'get_promoter_mining_rate', 'get_approver_mining_rate', 'get_rejecter_mining_rate', 'check_challenge_package', 'buy_challenge_package', 'challenge_reserve', 'load_challenge_reserve', 'is_challenge_closed', 'is_challenge_open', 'submission_number', 'challenge_expiry_date', 'submission_approver_number', 'submission_rejecter_number', 'submission_expiry_date']


def Main(operation, args):
    """

    :param operation: str The name of the operation to perform
    :param args: list A list of arguments along with the operation
    :return:
        bytearray: The result of the operation
    """

    trigger = GetTrigger()

    # This is used in the Verification portion of the contract
    # To determine whether a transfer of system assets ( NEO/Gas) involving
    # This contract's address can proceed
    if trigger == Verification():

        # check if the invoker is the owner of this contract
        is_owner = CheckWitness(TOKEN_OWNER)

        # If owner, proceed
        if is_owner:
            return True

        # Otherwise, we need to lookup the assets and determine
        # If attachments of assets is ok
        attachments = get_asset_attachments()

        #V1
        if attachments[4]:
            return False

        return can_exchange(ctx, attachments, True)

    elif trigger == Application():

        for op in NEP5_METHODS:
            if operation == op:
                return handle_nep51(ctx, operation, args)

        for op in MINING_METHODS:
            if operation == op:
                return handle_mining(ctx, operation, args)
        
        if operation == 'deploy':
            return deploy()

        elif operation == 'circulation':
            return get_circulation(ctx)

        # the following are handled by crowdsale

        elif operation == 'mintTokens':
            return perform_exchange(ctx)

        elif operation == 'crowdsale_register':
            return kyc_register(ctx, args)

        elif operation == 'crowdsale_status':
            return kyc_status(ctx, args)

        elif operation == 'crowdsale_available':
            return crowdsale_available_amount(ctx)

        elif operation == 'reallocate':
            return reallocate()

        elif operation == 'get_attachments':
            return get_asset_attachments()

        #V17
        elif operation == 'supportedStandards':
            return ['NEP-5', 'NEP-10']

        elif operation == 'migrate':
            #V11
            if len(args) != 8:
                return False
            if not CheckWitness(TOKEN_OWNER):
                return False
            Migrate(args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7])
            return True

        elif operation == 'destroy':
            #V11
            if not CheckWitness(TOKEN_OWNER):   
                return False
            Destroy()
            return True

        return 'unknown operation'

    return False


def deploy():
    """

    :return:
        bool: Whether the operation was successful
    """
    if not CheckWitness(TOKEN_OWNER):
        print("Must be owner to deploy")
        return False

    if not Get(ctx, 'initialized'):
        # do deploy logic
        Put(ctx, 'initialized', 1)

        # Allocate owner balance of 41 m
        Put(ctx, TOKEN_OWNER, TOKEN_OWNER_AMOUNT)

        # Allocate Challenge Reserve balance
        Put(ctx, CHALLENGE_SYSTEM_RESERVE, CHALLENGE_SYSTEM_INITIAL_AMOUNT)
        
        circulation = TOKEN_OWNER_AMOUNT + CHALLENGE_SYSTEM_INITIAL_AMOUNT

        Log("Deployed successfully!")

        # Add owner balance and challenge reserve balance to circulation
        return add_to_circulation(ctx, circulation)

    return False

def reallocate():
    """
    
    Once the token sale is over, the owner can take back the remaining tokens.
    :return:
        bool: Whether the operation was successful
    """
    if not CheckWitness(TOKEN_OWNER):
        print("Must be owner to reallocate")
        return False

    time = GetTime()

    if time < SERIES_A_END:
        print("Must wait until the end of Series A before re-allocating.")
        return False

    current_balance = Get(ctx, TOKEN_OWNER)

    crowdsale_available = crowdsale_available_amount(ctx)

    new_balance = current_balance + crowdsale_available

    Put(ctx, TOKEN_OWNER, new_balance)

    Log("Reallocated successfully!")

    # V14
    return add_to_circulation(ctx, crowdsale_available)