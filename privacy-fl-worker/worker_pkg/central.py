from vantage6.algorithm.tools.decorators import algorithm_client
from vantage6.algorithm.client import AlgorithmClient
from vantage6.algorithm.tools.util import info


@algorithm_client
def central(client: AlgorithmClient,
            cp_org_ids: list,
            as_org_id: int,
            encrypted_cp_contexts: dict,
            as_context: str,
            num_iterations: int = 2):
    """
    encrypted_cp_contexts: {str(org_id): {enc_key, nonce, enc_ctx}}
      — produced by the KDS algorithm, passed in by the researcher.
      — each CP only receives its own encrypted package.
    as_context: base64 CKKS context without secret key (safe to pass openly).
    """
    info('Central: Starting privacy-preserving FL')
    previous_result = 0.0
    all_iterations = []

    for i in range(num_iterations):
        info(f'Central: --- Iteration {i + 1} ---')

        # Each CP encrypts independently; receives only its own encrypted CKKS context
        enc_results = []
        for org_id in cp_org_ids:
            enc_task = client.task.create(
                input_={'method': 'cp_encrypt_partial', 'kwargs': {
                    'encrypted_cp_context': encrypted_cp_contexts[str(org_id)],
                    'previous_result': previous_result,
                }},
                organizations=[org_id],
                name=f'cp-encrypt-iter{i + 1}-org{org_id}'
            )
            enc_results.extend(client.wait_for_results(task_id=enc_task['id']))

        ciphertexts = [r['ciphertext'] for r in enc_results]

        # AS aggregates homomorphically — never has the secret key
        agg_task = client.task.create(
            input_={'method': 'as_aggregate_partial', 'kwargs': {
                'as_context_b64': as_context,
                'ciphertexts_b64': ciphertexts,
            }},
            organizations=[as_org_id],
            name=f'as-aggregate-iter{i + 1}'
        )
        agg_results = client.wait_for_results(task_id=agg_task['id'])
        aggregated = agg_results[0]['aggregated']

        # Each CP decrypts independently
        dec_results = []
        for org_id in cp_org_ids:
            dec_task = client.task.create(
                input_={'method': 'cp_decrypt_partial', 'kwargs': {
                    'encrypted_cp_context': encrypted_cp_contexts[str(org_id)],
                    'aggregated_ciphertext_b64': aggregated,
                }},
                organizations=[org_id],
                name=f'cp-decrypt-iter{i + 1}-org{org_id}'
            )
            dec_results.extend(client.wait_for_results(task_id=dec_task['id']))

        results_this_iter = [r['result'] for r in dec_results]
        previous_result = results_this_iter[0]
        all_iterations.append({
            'iteration': i + 1,
            'result': previous_result,
            'results_per_cp': results_this_iter,
        })
        info(f'Central: Iteration {i + 1} result = {previous_result:.4f}')

    return {'iterations': all_iterations, 'final_result': previous_result}
