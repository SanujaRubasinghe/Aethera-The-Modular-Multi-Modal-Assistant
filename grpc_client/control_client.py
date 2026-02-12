import grpc
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
grpc_proto_path = os.path.join(current_dir, "grpc_proto")
if grpc_proto_path not in sys.path:
    sys.path.append(grpc_proto_path)

import control_pb2
import control_pb2_grpc

class GRPCIntentClient:
    def __init__(self, host="localhost", port=50051):
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = control_pb2_grpc.CommandControllerStub(self.channel)

    def process_intents(self, intent_list, mode=control_pb2.SEQUENTIAL, rollback_on_error=True):
        proto_intents = [intent.to_proto() for intent in intent_list]
        request = control_pb2.ProcessIntentsRequest(
            intents=proto_intents,
            mode=mode,
            rollback_on_error=rollback_on_error
        )
        try:
            response = self.stub.ProcessIntents(request)
            return response
        except grpc.RpcError as e:
            print(f"gRPC error: {e}")
            return None