import { useMutation, useQueryClient } from "@tanstack/react-query";
import { submitApproval } from "../api/approvals";

export function useApprovalMutation(featureId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ artifactId, status, reviewer_comment, approved_by }) =>
      submitApproval(artifactId, { status, reviewer_comment, approved_by }),
    onSuccess: () => {
      // Approval is what advances the graph -- all queries must be invalidated so the UI
      // reflects the (possibly automatic, e.g. Domain/UI-UX/Coder) next stage as soon as
      // it's observable, rather than waiting for the next poll tick. approvals feeds the
      // activity timeline (M4).
      queryClient.invalidateQueries({ queryKey: ["graphStatus", featureId] });
      queryClient.invalidateQueries({ queryKey: ["artifacts", featureId] });
      queryClient.invalidateQueries({ queryKey: ["approvals", featureId] });
    },
  });
}
