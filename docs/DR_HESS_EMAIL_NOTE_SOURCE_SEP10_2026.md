Subject: Mycosoft ITDX26 - NLM/FormSpace methods and reproducible Weka evaluation

Dr. Hess,

Following your suggestion to test our algorithms in Weka, we have connected our native NLM/FormSpace numerical outputs to Weka's Java Evaluation API. The model generates the predictions; Weka evaluates the supplied distributions against withheld labels. The current integration covers pattern analysis and a defined same-environmental-event link task. Our associated advisory and map products have separate evaluation requirements.

The attached material includes our mathematical architecture paper, an operator runbook, a reproducible synthetic reference run and its source/artifact identities, plus an explanatory audio companion. A new Java replay completed on September 10 with 14/14 arithmetic checks passing. This replay rescored recorded model probabilities; it was not a new field-data collection or a production inference qualification.

We also tested ZeroR and J48 on the same clean synthetic Task 12 captures. A one-split J48 tree matched the reference model's perfect clean F1, which makes clear that this fixture is insufficient to establish an advantage from temporal learning or FormSpace. We are using it as an executable regression reference while designing a stronger held-out experiment around multisensor ambiguity, missingness, device/site shift and event warning time.

The stress suite exposes substantial degradation under sensor bias and explicit abstention for unsupported inputs. The current local trial criteria are not all met, and we are not presenting those criteria as Army requirements.

Could you confirm whether your preferred evaluation is through frozen-distribution Weka API scoring, a Weka Classifier interface, or another organizer-provided harness? We would also appreciate the task-specific target definitions, test-data and holdout protocol, any required prediction horizons, and the meaning of the 1-5 assessment scale.

Our next objective is an evaluator-relevant, forward-only experiment that connects a prediction to a useful environmental warning or evidence-collection response, with independently assessed outcomes and a complete evidence trail.

Thank you,
Morgan Rockwell
Mycosoft

---

Attachment note for Morgan: include the audio only after reviewing it against the written sources. This is a draft for you to send; no email has been sent by this assistant.
